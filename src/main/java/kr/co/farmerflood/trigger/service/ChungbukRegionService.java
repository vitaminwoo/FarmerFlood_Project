package kr.co.farmerflood.trigger.service;

import java.util.*;
import org.springframework.stereotype.Service;

@Service
public class ChungbukRegionService {
    private final Map<String,List<String>> localities = new LinkedHashMap<>();
    private final Map<String,Point> centers = new HashMap<>();
    public ChungbukRegionService(){
        localities.put("청주시", list("낭성면,미원면,가덕면,남일면,문의면,중앙동,성안동,탑대성동,영운동,금천동,용담명암산성동,용암1동,용암2동,남이면,현도면,사직1동,사직2동,모충동,산남동,분평동,수곡1동,수곡2동,성화개신죽림동,오송읍,강내면,옥산면,운천신봉동,복대1동,복대2동,가경동,봉명1동,봉명2송정동,강서1동,강서2동,내수읍,오창읍,북이면,우암동,내덕1동,내덕2동,율량사천동,오근장동"));
        localities.put("충주시", list("주덕읍,살미면,수안보면,대소원면,신니면,노은면,앙성면,중앙탑면,금가면,동량면,산척면,엄정면,소태면,성내충인동,교현안림동,교현2동,용산동,지현동,문화동,호암직동,달천동,봉방동,칠금금릉동,연수동,목행용탄동"));
        localities.put("제천시", list("봉양읍,금성면,청풍면,수산면,덕산면,한수면,백운면,송학면,교동,의림지동,중앙동,남현동,영서동,용두동,신백동,청전동,화산동"));
        localities.put("보은군", list("보은읍,속리산면,장안면,마로면,탄부면,삼승면,수한면,회남면,회인면,내북면,산외면"));
        localities.put("옥천군", list("옥천읍,동이면,안남면,안내면,청성면,청산면,이원면,군서면,군북면"));
        localities.put("영동군", list("영동읍,용산면,황간면,추풍령면,매곡면,상촌면,양강면,용화면,학산면,양산면,심천면"));
        localities.put("증평군", list("증평읍,도안면"));
        localities.put("진천군", list("진천읍,덕산읍,초평면,문백면,백곡면,이월면,광혜원면"));
        localities.put("괴산군", list("괴산읍,감물면,장연면,연풍면,칠성면,문광면,청천면,청안면,사리면,소수면,불정면"));
        localities.put("음성군", list("음성읍,금왕읍,소이면,원남면,맹동면,대소면,삼성면,생극면,감곡면"));
        localities.put("단양군", list("단양읍,매포읍,대강면,가곡면,영춘면,어상천면,적성면,단성면"));
        centers.put("청주시",new Point(36.6424,127.4890));centers.put("충주시",new Point(36.9910,127.9259));centers.put("제천시",new Point(37.1326,128.1910));centers.put("보은군",new Point(36.4894,127.7295));centers.put("옥천군",new Point(36.3064,127.5714));centers.put("영동군",new Point(36.1750,127.7834));centers.put("증평군",new Point(36.7854,127.5815));centers.put("진천군",new Point(36.8554,127.4356));centers.put("괴산군",new Point(36.8154,127.7867));centers.put("음성군",new Point(36.9403,127.6905));centers.put("단양군",new Point(36.9845,128.3655));
    }
    private List<String> list(String csv){return List.of(csv.split(","));}
    public RegionView view(){return new RegionView("충청북도",localities);}
    public Point point(String district,String locality){
        if("청주시".equals(district)&&"강내면".equals(locality))return new Point(36.6229,127.3577);
        if("보은군".equals(district)&&"속리산면".equals(locality))return new Point(36.5564,127.7806);
        return Optional.ofNullable(centers.get(district)).orElseThrow(()->new IllegalArgumentException("지원하지 않는 충북 시·군입니다."));
    }
    public void validate(String district,String locality){if(!localities.getOrDefault(district,List.of()).contains(locality))throw new IllegalArgumentException("지원하지 않는 읍·면·동입니다.");}
    public record Point(double latitude,double longitude){}
    public record RegionView(String province,Map<String,List<String>> districts){}
}
