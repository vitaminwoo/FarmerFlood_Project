#!/usr/bin/env python3
"""Official Korean Farm Map Shapefile ZIP -> PostGIS importer."""
import argparse, io, os, unicodedata, zipfile
from pathlib import PurePosixPath
import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import shape, MultiPolygon, Polygon
from shapely.ops import transform
from shapely.validation import make_valid
import psycopg

def decoded_name(name):
    try: name=name.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError,UnicodeDecodeError): pass
    return unicodedata.normalize("NFC",name)

def region(address):
    tokens=address.split(); district=next((x for x in tokens if x.endswith(("시","군")) and x!="충청북도"),"")
    locality=next((x for x in tokens if x.endswith(("읍","면","동"))),"")
    return district,locality

def multipolygon(geometry):
    geometry=make_valid(geometry)
    if isinstance(geometry,Polygon): return MultiPolygon([geometry])
    if isinstance(geometry,MultiPolygon): return geometry
    polygons=[g for g in getattr(geometry,"geoms",[]) if isinstance(g,Polygon)]
    return MultiPolygon(polygons) if polygons else None

def dataset_members(archive):
    groups={}
    for info in archive.infolist():
        name=decoded_name(info.filename)
        suffix=PurePosixPath(name).suffix.lower()
        if suffix in {".shp",".shx",".dbf",".prj",".cpg"}: groups.setdefault(str(PurePosixPath(name).with_suffix("")),{})[suffix]=info
    return [parts for parts in groups.values() if {".shp",".shx",".dbf",".prj"}.issubset(parts)]

def main():
    p=argparse.ArgumentParser();p.add_argument("zip");p.add_argument("--district");p.add_argument("--locality");p.add_argument("--batch-size",type=int,default=500);args=p.parse_args()
    db_url=os.getenv("DB_URL","jdbc:postgresql://127.0.0.1:5432/farmer_flood").removeprefix("jdbc:")
    db_user=os.getenv("DB_USERNAME","farmer_flood");db_password=os.getenv("DB_PASSWORD","farmer_flood")
    connection_url=db_url.replace("postgresql://",f"postgresql://{db_user}:{db_password}@",1)
    sql="""INSERT INTO farm_map_parcel(source_id,uid,pnu,crop_type,area_sqm,address,province,district,locality,source_year,geometry)
             VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,2025,ST_Multi(ST_GeomFromText(%s,4326)))
             ON CONFLICT(source_id) DO UPDATE SET pnu=excluded.pnu,crop_type=excluded.crop_type,area_sqm=excluded.area_sqm,address=excluded.address,province=excluded.province,district=excluded.district,locality=excluded.locality,source_year=excluded.source_year,geometry=excluded.geometry"""
    total=0
    with zipfile.ZipFile(args.zip) as archive,psycopg.connect(connection_url) as conn:
      for files in dataset_members(archive):
        prj=archive.read(files[".prj"]).decode("utf-8",errors="replace");transformer=Transformer.from_crs(CRS.from_wkt(prj),"EPSG:4326",always_xy=True)
        reader=shapefile.Reader(shp=io.BytesIO(archive.read(files[".shp"])),shx=io.BytesIO(archive.read(files[".shx"])),dbf=io.BytesIO(archive.read(files[".dbf"])),encoding="euc-kr")
        fields=[f.name for f in reader.fields[1:]];batch=[];dataset_count=0
        for sr in reader.iterShapeRecords():
            data=dict(zip(fields,sr.record));address=(data.get("STDG_ADDR") or "").strip();district,locality=region(address)
            if args.district and district!=args.district: continue
            if args.locality and locality!=args.locality: continue
            geom=multipolygon(transform(transformer.transform,shape(sr.shape.__geo_interface__)))
            if geom is None or geom.is_empty: continue
            batch.append((str(data.get("ID") or data.get("UID")),str(data.get("UID") or ""),str(data.get("PNU") or ""),str(data.get("CLSF_NM") or "농경지"),float(data.get("AREA") or geom.area),address,"충청북도",district,locality,geom.wkt))
            if len(batch)>=args.batch_size:
                with conn.cursor() as cur: cur.executemany(sql,batch)
                conn.commit();total+=len(batch);dataset_count+=len(batch);batch=[];print(f"imported {total:,}",flush=True)
        if batch:
            with conn.cursor() as cur: cur.executemany(sql,batch)
            conn.commit();total+=len(batch);dataset_count+=len(batch)
        if dataset_count: print(f"dataset complete: {dataset_count:,}",flush=True)
    print(f"Farm Map import complete: {total:,} parcels")
if __name__=="__main__": main()
