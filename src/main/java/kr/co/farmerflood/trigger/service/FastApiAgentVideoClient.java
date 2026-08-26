package kr.co.farmerflood.trigger.service;

import java.nio.file.*;import kr.co.farmerflood.trigger.config.AppProperties;
import org.springframework.core.io.FileSystemResource;import org.springframework.core.io.buffer.DataBufferUtils;import org.springframework.http.client.MultipartBodyBuilder;import org.springframework.stereotype.Component;import org.springframework.web.reactive.function.BodyInserters;import org.springframework.web.reactive.function.client.WebClient;

public class FastApiAgentVideoClient implements AgentVideoClient {
    private final AppProperties props;private final WebClient web;
    public FastApiAgentVideoClient(AppProperties p,WebClient.Builder b){props=p;web=b.build();}
    public String submit(VideoProductionJob job,Path recording){MultipartBodyBuilder m=new MultipartBodyBuilder();m.part("location",job.getAlert().address());m.part("farmer_name",props.getPipeline().getAgent().getFarmerName());m.part("storage_name",job.getStorageName());m.part("mode",props.getPipeline().getAgent().getMode());m.part("video",new FileSystemResource(recording));AgentResponse r=web.post().uri(base()+"/api/jobs").body(BodyInserters.fromMultipartData(m.build())).retrieve().bodyToMono(AgentResponse.class).block();if(r==null||r.job_id()==null)throw new IllegalStateException("FastAPI가 job_id를 반환하지 않았습니다.");return r.job_id();}
    public AgentStatus status(String id,Path destination){AgentResponse r=web.get().uri(base()+"/api/jobs/{id}",id).retrieve().bodyToMono(AgentResponse.class).block();if(r==null)return new AgentStatus(AgentStatus.State.FAILED,null,null,"빈 Agent 상태 응답");if("FAILED".equalsIgnoreCase(r.status()))return new AgentStatus(AgentStatus.State.FAILED,r.message(),null,r.error());if(!"DONE".equalsIgnoreCase(r.status()))return new AgentStatus(AgentStatus.State.RUNNING,r.message(),null,null);try{Files.createDirectories(destination.getParent());DataBufferUtils.write(web.get().uri(base()+"/api/jobs/{id}/video",id).retrieve().bodyToFlux(org.springframework.core.io.buffer.DataBuffer.class),destination).block();return new AgentStatus(AgentStatus.State.DONE,r.message(),destination,null);}catch(Exception e){return new AgentStatus(AgentStatus.State.FAILED,r.message(),null,e.getMessage());}}
    private String base(){return props.getPipeline().getAgent().getBaseUrl().replaceAll("/$","");}
    private record AgentResponse(String job_id,String status,String message,String result_url,String error){}
}
