package kr.co.farmerflood.trigger.service;

import java.time.Instant;
import java.util.*;
import kr.co.farmerflood.trigger.domain.StationSummary;
import kr.co.farmerflood.trigger.persistence.*;
import kr.co.farmerflood.trigger.provider.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class FarmlandService {
    private final AppUserJpaRepository users;
    private final FarmlandJpaRepository farmlands;
    private final FarmlandStationJpaRepository links;
    private final WaterStationCatalogue stations;

    public FarmlandService(AppUserJpaRepository users, FarmlandJpaRepository farmlands,
                           FarmlandStationJpaRepository links, WaterStationCatalogue stations) {
        this.users=users; this.farmlands=farmlands; this.links=links; this.stations=stations;
    }

    @Transactional
    public UserView createUser(String email, String name) {
        if (users.existsByEmail(email)) throw new IllegalArgumentException("이미 등록된 이메일입니다.");
        AppUserEntity entity = new AppUserEntity(); entity.id=UUID.randomUUID().toString(); entity.email=email;
        entity.name=name; entity.role="FARMER"; entity.createdAt=Instant.now(); users.save(entity); return view(entity);
    }

    @Transactional
    public UserView createMobileUser(String name, String phone) {
        String normalized = normalizePhone(phone);
        if (users.existsByPhone(normalized)) throw new IllegalArgumentException("이미 가입된 전화번호입니다.");
        AppUserEntity entity = new AppUserEntity(); entity.id=UUID.randomUUID().toString();
        entity.email=normalized+"@mobile.farmer-flood.local"; entity.name=name.trim(); entity.phone=normalized;entity.role="FARMER";
        entity.createdAt=Instant.now(); users.save(entity); return view(entity);
    }

    @Transactional public UserView createGuardian(String guardianName,String farmerName,String farmerPhone){AppUserEntity farmer=users.findByNameAndPhone(farmerName.trim(),normalizePhone(farmerPhone)).filter(x->x.role==null||"FARMER".equals(x.role)).orElseThrow(()->new IllegalArgumentException("가입한 농업인 정보를 찾을 수 없습니다."));if(users.findByNameAndTargetFarmerId(guardianName.trim(),farmer.id).isPresent())throw new IllegalArgumentException("이미 등록된 보호자입니다.");AppUserEntity guardian=new AppUserEntity();guardian.id=UUID.randomUUID().toString();guardian.email="guardian-"+guardian.id+"@mobile.farmer-flood.local";guardian.name=guardianName.trim();guardian.role="GUARDIAN";guardian.targetFarmerId=farmer.id;guardian.createdAt=Instant.now();users.save(guardian);return view(guardian);}
    public Optional<UserView> authenticateGuardian(String guardianName,String farmerName,String farmerPhone){return users.findByNameAndPhone(farmerName.trim(),normalizePhone(farmerPhone)).flatMap(f->users.findByNameAndTargetFarmerId(guardianName.trim(),f.id)).map(this::view);}

    public Optional<UserView> authenticate(String name,String phone){return users.findByNameAndPhone(name.trim(),normalizePhone(phone)).map(this::view);}
    public UserView user(String id){return users.findById(id).map(this::view).orElseThrow(()->new NoSuchElementException("사용자를 찾을 수 없습니다."));}

    @Transactional
    public FarmlandView register(RegisterFarmland request) {
        if (!users.existsById(request.userId())) throw new NoSuchElementException("사용자를 찾을 수 없습니다.");
        var grid=KmaGridConverter.from(request.latitude(),request.longitude()); FarmlandEntity farm=new FarmlandEntity();
        farm.id=UUID.randomUUID().toString(); farm.userId=request.userId(); farm.name=request.name(); farm.address=request.address();
        farm.province=request.province(); farm.district=request.district(); farm.locality=request.locality();farm.sourceParcelId=request.sourceParcelId();farm.pnu=request.pnu();farm.areaSquareMeters=request.areaSquareMeters();
        farm.latitude=request.latitude(); farm.longitude=request.longitude(); farm.boundaryGeoJson=request.boundaryGeoJson();
        farm.regionId=request.regionId()==null||request.regionId().isBlank()?"chungbuk-"+grid.nx()+"-"+grid.ny():request.regionId();
        farm.active=true; farm.createdAt=Instant.now(); farm.updatedAt=farm.createdAt; farmlands.save(farm); linkNearest(farm); return view(farm);
    }

    @Transactional public FarmlandView relink(String id){FarmlandEntity f=farmlands.findById(id).orElseThrow();links.deleteByFarmlandId(id);linkNearest(f);return view(f);}
    public List<FarmlandView> byUser(String id){return farmlands.findByUserIdOrderByCreatedAtDesc(id).stream().map(this::view).toList();}
    public List<FarmlandView> all(){return farmlands.findAll().stream().map(this::view).toList();}
    public List<FarmlandEntity> activeIn(String district,String locality){return farmlands.findByActiveTrueAndDistrictAndLocality(district,locality);}

    private void linkNearest(FarmlandEntity farm){
        if("청주시".equals(farm.district)&&"강내면".equals(farm.locality)){FarmlandStationEntity demo=new FarmlandStationEntity();demo.id=UUID.randomUUID().toString();demo.farmlandId=farm.id;demo.stationCode="MOCK-004";demo.stationName="강내면_mock_4 (시연)";demo.stationLatitude=36.6229;demo.stationLongitude=127.3577;demo.distanceMeters=distance(farm.latitude,farm.longitude,demo.stationLatitude,demo.stationLongitude);demo.priorityOrder=0;demo.active=true;demo.linkedAt=Instant.now();links.save(demo);}
        List<StationDistance> nearest=stations.chungbukStations().stream().filter(s->Double.isFinite(s.latitude())&&Double.isFinite(s.longitude())&&s.thresholds().complete())
            .map(s->new StationDistance(s,distance(farm.latitude,farm.longitude,s.latitude(),s.longitude())))
            .filter(x->x.meters<=50_000).sorted(Comparator.comparingDouble(x->x.meters)).limit(3).toList();
        int priority=1; for(var x:nearest){FarmlandStationEntity l=new FarmlandStationEntity();l.id=UUID.randomUUID().toString();l.farmlandId=farm.id;l.stationCode=x.station.stationCode();l.stationName=x.station.stationName();l.stationLatitude=x.station.latitude();l.stationLongitude=x.station.longitude();l.distanceMeters=x.meters;l.priorityOrder=priority++;l.active=true;l.linkedAt=Instant.now();links.save(l);}
    }
    private FarmlandView view(FarmlandEntity f){var related=links.findByFarmlandIdOrderByPriorityOrder(f.id).stream().map(l->new StationLinkView(l.stationCode,l.stationName,l.distanceMeters,l.priorityOrder,l.active)).toList();return new FarmlandView(f.id,f.userId,f.name,f.address,f.province,f.district,f.locality,f.sourceParcelId,f.pnu,f.areaSquareMeters,f.latitude,f.longitude,f.boundaryGeoJson,f.regionId,f.active,related,f.createdAt,f.updatedAt);}
    private UserView view(AppUserEntity e){return new UserView(e.id,e.email,e.name,e.phone,e.role==null?"FARMER":e.role,e.targetFarmerId,e.createdAt);}
    private String normalizePhone(String value){String phone=value==null?"":value.replaceAll("[^0-9]","");if(phone.length()<10||phone.length()>11)throw new IllegalArgumentException("전화번호를 확인해주세요.");return phone;}
    private double distance(double a,double b,double c,double d){double p1=Math.toRadians(a),p2=Math.toRadians(c),dp=Math.toRadians(c-a),dl=Math.toRadians(d-b);double x=Math.sin(dp/2)*Math.sin(dp/2)+Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)*Math.sin(dl/2);return 6_371_008.8*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));}
    private record StationDistance(StationSummary station,double meters){}
    public record RegisterFarmland(String userId,String name,String address,String province,String district,String locality,String sourceParcelId,String pnu,Double areaSquareMeters,double latitude,double longitude,String boundaryGeoJson,String regionId){}
    public record UserView(String id,String email,String name,String phone,String role,String targetFarmerId,Instant createdAt){}
    public record StationLinkView(String stationCode,String stationName,double distanceMeters,int priority,boolean active){}
    public record FarmlandView(String id,String userId,String name,String address,String province,String district,String locality,String sourceParcelId,String pnu,Double areaSquareMeters,double latitude,double longitude,String boundaryGeoJson,String regionId,boolean active,List<StationLinkView> monitoringStations,Instant createdAt,Instant updatedAt){}
}
