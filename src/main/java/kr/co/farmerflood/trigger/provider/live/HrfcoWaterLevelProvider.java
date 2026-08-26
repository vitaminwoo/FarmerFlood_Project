package kr.co.farmerflood.trigger.provider.live;
import tools.jackson.databind.JsonNode;
import java.time.*; import java.time.format.DateTimeFormatter; import java.util.Comparator; import java.util.stream.StreamSupport;
import kr.co.farmerflood.trigger.config.AppProperties; import kr.co.farmerflood.trigger.domain.WaterLevelObservation; import kr.co.farmerflood.trigger.provider.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty; import org.springframework.stereotype.Component; import org.springframework.web.reactive.function.client.WebClient;
@Component @ConditionalOnProperty(name="app.provider-mode",havingValue="live")
public class HrfcoWaterLevelProvider implements WaterLevelProvider {
 private static final DateTimeFormatter TIME=DateTimeFormatter.ofPattern("yyyyMMddHHmm"); private final AppProperties p; private final WebClient client;
 public HrfcoWaterLevelProvider(AppProperties p,WebClient.Builder b){this.p=p;client=b.baseUrl(p.getHrfco().getBaseUrl()).build();}
 public WaterLevelObservation latest(AppProperties.Location l){
  if(p.getHrfco().getApiKey().isBlank())throw new ProviderException("HRFCO","HRFCO_API_KEY is missing");
  JsonNode body=client.get().uri("/{key}/waterlevel/list/10M/{station}.json",p.getHrfco().getApiKey(),l.getStationCode()).retrieve().bodyToMono(JsonNode.class).block(Duration.ofSeconds(20));
  if(body==null||!"200".equals(body.path("code").asText("200")))throw new ProviderException("HRFCO",body==null?"empty response":"code="+body.path("code").asText());
  JsonNode content=body.path("content"); if(!content.isArray()||content.isEmpty())throw new ProviderException("HRFCO","no water-level data");
  JsonNode n=StreamSupport.stream(content.spliterator(),false).max(Comparator.comparing(x->x.path("ymdhm").asText())).orElseThrow();
  double level=n.path("wl").asDouble(Double.NaN); if(!Double.isFinite(level))throw new ProviderException("HRFCO","invalid water level");
  return new WaterLevelObservation(l.getStationCode(),l.getStationName(),level,RiskClassifier.classify(level,l.getThresholds()),parse(n.path("ymdhm").asText()));
 }
 private Instant parse(String s){try{return LocalDateTime.parse(s.replaceAll("[^0-9]","").substring(0,12),TIME).atZone(ZoneId.of("Asia/Seoul")).toInstant();}catch(RuntimeException e){return Instant.now();}}
}
