package kr.co.farmerflood.trigger.service;

import java.nio.file.*;import java.util.LinkedHashMap;import java.util.Map;
import kr.co.farmerflood.trigger.config.AppProperties;import kr.co.farmerflood.trigger.domain.AlertEvent;
import org.springframework.core.io.buffer.DataBufferUtils;import org.springframework.stereotype.Component;import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.core.ParameterizedTypeReference;import reactor.core.publisher.Mono;

@Component
public class FloodVideoWorkflowClient {
    public enum State { RUNNING, DONE, FAILED }
    public record WorkflowStatus(State state,String stage,String message,int progress,Path localFile,String error){}
    private final AppProperties props;private final WebClient web;
    public FloodVideoWorkflowClient(AppProperties p,WebClient.Builder b){props=p;web=b.build();}
    public String submit(VideoProductionJob job){AlertEvent a=job.getAlert();Map<String,Object> body=new LinkedHashMap<>();body.put("alert_id",a.id());body.put("storage_name",job.getStorageName());body.put("station_code",a.stationCode());body.put("station_name",a.stationName());body.put("address",a.address());body.put("nx",a.nx());body.put("ny",a.ny());body.put("water_level_meters",a.waterLevelMeters());body.put("risk_level",a.riskLevel().name());body.put("forecast_rainfall_mm",a.forecastRainfallMm());body.put("triggered_at",a.triggeredAt().toString());body.put("farmer_name",props.getPipeline().getWorker().getFarmerName());body.put("user_id",a.userId());body.put("farmland_id",a.farmlandId());body.put("region_id",a.address());body.put("workflow_version",props.getPipeline().getWorker().getWorkflowVersion());body.put("scenario_version",props.getPipeline().getWorker().getScenarioVersion());body.put("v23_field_profile_id",props.getPipeline().getWorker().getV23FieldProfileId());body.put("v23_profile_user_id",props.getPipeline().getWorker().getV23ProfileUserId());WorkerResponse r=web.post().uri(base()+"/api/workflows").bodyValue(body).retrieve().bodyToMono(WorkerResponse.class).block();if(r==null||r.job_id()==null)throw new IllegalStateException("팀 flood worker가 job_id를 반환하지 않았습니다.");return r.job_id();}
    public WorkflowStatus status(String id,Path destination){WorkerResponse r=web.get().uri(base()+"/api/workflows/{id}",id).retrieve().bodyToMono(WorkerResponse.class).block();if(r==null)return new WorkflowStatus(State.FAILED,"failed","빈 Worker 상태 응답",0,null,"빈 Worker 상태 응답");int progress=r.progress()==null?0:r.progress();if("FAILED".equalsIgnoreCase(r.status()))return new WorkflowStatus(State.FAILED,r.stage(),r.message(),progress,null,r.error());if(!"DONE".equalsIgnoreCase(r.status()))return new WorkflowStatus(State.RUNNING,r.stage(),r.message(),progress,null,null);try{Files.createDirectories(destination.getParent());DataBufferUtils.write(web.get().uri(base()+"/api/workflows/{id}/video",id).retrieve().bodyToFlux(org.springframework.core.io.buffer.DataBuffer.class),destination).block();return new WorkflowStatus(State.DONE,r.stage(),r.message(),100,destination,null);}catch(Exception e){return new WorkflowStatus(State.FAILED,"download","최종 영상 다운로드 실패",progress,null,e.getMessage());}}
    public Mono<Map<String,Object>> detail(String id){return web.get().uri(base()+"/api/workflows/{id}/detail",id).retrieve().bodyToMono(new ParameterizedTypeReference<>(){});}
    public Mono<Map<String,Object>> logs(String id,String source,long after){String uri=org.springframework.web.util.UriComponentsBuilder.fromUriString(base()).path("/api/workflows/{id}/logs").queryParam("source",source).queryParam("after",after).buildAndExpand(id).encode().toUriString();return web.get().uri(uri).retrieve().bodyToMono(new ParameterizedTypeReference<>(){});}
    private String base(){return props.getPipeline().getWorker().getBaseUrl().replaceAll("/$","");}
    private record WorkerResponse(String job_id,String status,String stage,String message,Integer progress,String result_url,String error){}
}
