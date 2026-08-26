package kr.co.farmerflood.trigger.provider.live;
import tools.jackson.databind.JsonNode; import java.time.*; import java.time.format.DateTimeFormatter; import java.util.List;
import kr.co.farmerflood.trigger.config.AppProperties; import kr.co.farmerflood.trigger.domain.*; import kr.co.farmerflood.trigger.provider.WeatherForecastProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty; import org.springframework.stereotype.Component; import org.springframework.web.reactive.function.client.WebClient;
@Component @ConditionalOnProperty(name="app.provider-mode",havingValue="live")
public class KmaWeatherForecastProvider implements WeatherForecastProvider {
 private static final ZoneId KST=ZoneId.of("Asia/Seoul"); private static final List<Integer> HOURS=List.of(2,5,8,11,14,17,20,23); private final AppProperties p; private final WebClient client;
 public KmaWeatherForecastProvider(AppProperties p,WebClient.Builder b){this.p=p;client=b.baseUrl(p.getKma().getBaseUrl()).build();}
 public RainfallTimeline timeline(int nx,int ny,int hours){
  if(p.getKma().getServiceKey().isBlank())throw new ProviderException("KMA","KMA_SERVICE_KEY is missing"); LocalDateTime base=latestPublishedBase(LocalDateTime.now(KST));
  JsonNode body=client.get().uri(b->b.path("/getVilageFcst").queryParam("serviceKey",p.getKma().getServiceKey()).queryParam("pageNo",1).queryParam("numOfRows",1000).queryParam("dataType","JSON").queryParam("base_date",base.format(DateTimeFormatter.BASIC_ISO_DATE)).queryParam("base_time",base.format(DateTimeFormatter.ofPattern("HHmm"))).queryParam("nx",nx).queryParam("ny",ny).build()).retrieve().bodyToMono(JsonNode.class).block(Duration.ofSeconds(20));
  String code=body==null?"EMPTY":body.path("response").path("header").path("resultCode").asText(); if(!"00".equals(code))throw new ProviderException("KMA","resultCode="+code);
  Instant now=Instant.now(),end=now.plus(Duration.ofHours(hours)); double total=0;java.util.ArrayList<HourlyRainfall> timeline=new java.util.ArrayList<>();
  for(JsonNode i:body.path("response").path("body").path("items").path("item")){if(!"PCP".equals(i.path("category").asText()))continue;Instant at=forecastInstant(i.path("fcstDate").asText(),i.path("fcstTime").asText());if(!at.isBefore(now)&&!at.isAfter(end)){String raw=i.path("fcstValue").asText();double mm=KmaRainfallParser.millimeters(raw);total+=mm;timeline.add(new HourlyRainfall(at,raw,mm));}}
  timeline.sort(java.util.Comparator.comparing(HourlyRainfall::forecastAt));
  return new RainfallTimeline(nx,ny,hours,base.atZone(KST).toInstant(),total,java.util.List.copyOf(timeline));
 }
 static LocalDateTime latestPublishedBase(LocalDateTime now){LocalDateTime safe=now.minusMinutes(15);int h=HOURS.stream().filter(x->x<=safe.getHour()).reduce((a,b)->b).orElse(-1);return h>=0?LocalDateTime.of(safe.toLocalDate(),LocalTime.of(h,0)):LocalDateTime.of(safe.toLocalDate().minusDays(1),LocalTime.of(23,0));}
 private Instant forecastInstant(String d,String t){return LocalDateTime.parse(d+String.format("%04d",Integer.parseInt(t)),DateTimeFormatter.ofPattern("yyyyMMddHHmm")).atZone(KST).toInstant();}
}
