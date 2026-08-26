package kr.co.farmerflood.trigger.service;

import jakarta.annotation.PostConstruct;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class FarmMapService {
    private final JdbcTemplate jdbc;
    public FarmMapService(JdbcTemplate jdbc){this.jdbc=jdbc;}

    @PostConstruct
    void ensureSchema(){
        String product=jdbc.execute((org.springframework.jdbc.core.ConnectionCallback<String>)c->c.getMetaData().getDatabaseProductName());
        if(product==null||!product.toLowerCase(Locale.ROOT).contains("postgresql")){
            jdbc.execute("CREATE TABLE IF NOT EXISTS farm_map_parcel (source_id varchar(32) PRIMARY KEY,uid varchar(32),pnu varchar(19),crop_type varchar(40),area_sqm double,address varchar(300),province varchar(40),district varchar(40),locality varchar(60),source_year integer,geometry clob NOT NULL)");
            return;
        }
        jdbc.execute("CREATE EXTENSION IF NOT EXISTS postgis");
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS farm_map_parcel (
              source_id varchar(32) PRIMARY KEY,
              uid varchar(32), pnu varchar(19), crop_type varchar(40),
              area_sqm double precision, address varchar(300), province varchar(40),
              district varchar(40), locality varchar(60), source_year integer,
              geometry geometry(MultiPolygon,4326) NOT NULL
            )
            """);
        jdbc.execute("CREATE INDEX IF NOT EXISTS idx_farm_map_geometry ON farm_map_parcel USING GIST (geometry)");
        jdbc.execute("CREATE INDEX IF NOT EXISTS idx_farm_map_region ON farm_map_parcel (district, locality)");
    }

    public String parcels(String district,String locality,double minLon,double minLat,double maxLon,double maxLat){
        return jdbc.queryForObject("""
            SELECT json_build_object('type','FeatureCollection','features',COALESCE(json_agg(ST_AsGeoJSON(row_data.*)::json),'[]'::json))::text
            FROM (
              SELECT source_id AS id,pnu,crop_type,area_sqm,address,geometry
              FROM farm_map_parcel
              WHERE district=? AND locality=?
                AND geometry && ST_MakeEnvelope(?,?,?,?,4326)
              ORDER BY area_sqm DESC NULLS LAST LIMIT 2000
            ) row_data
            """,String.class,district,locality,minLon,minLat,maxLon,maxLat);
    }

    public Parcel parcel(String id){
        return jdbc.queryForObject("""
            SELECT source_id,pnu,crop_type,area_sqm,address,province,district,locality,
                   ST_Y(ST_PointOnSurface(geometry)),ST_X(ST_PointOnSurface(geometry)),ST_AsGeoJSON(geometry)
            FROM farm_map_parcel WHERE source_id=?
            """,(rs,n)->new Parcel(rs.getString(1),rs.getString(2),rs.getString(3),(Double)rs.getObject(4),rs.getString(5),rs.getString(6),rs.getString(7),rs.getString(8),rs.getDouble(9),rs.getDouble(10),rs.getString(11)),id);
    }
    public long count(String district,String locality){return Optional.ofNullable(jdbc.queryForObject("SELECT count(*) FROM farm_map_parcel WHERE district=? AND locality=?",Long.class,district,locality)).orElse(0L);}
    public record Parcel(String id,String pnu,String cropType,Double areaSquareMeters,String address,String province,String district,String locality,double latitude,double longitude,String geometryGeoJson){}
}
