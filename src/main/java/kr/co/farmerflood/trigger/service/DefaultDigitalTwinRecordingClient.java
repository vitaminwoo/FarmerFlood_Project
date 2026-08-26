package kr.co.farmerflood.trigger.service;

import java.nio.file.*;import java.time.Instant;import java.util.*;import java.util.concurrent.ConcurrentHashMap;
import kr.co.farmerflood.trigger.config.AppProperties;import kr.co.farmerflood.trigger.domain.AlertEvent;
import org.springframework.core.io.buffer.DataBufferUtils;import org.springframework.stereotype.Component;import org.springframework.web.reactive.function.client.WebClient;

public class DefaultDigitalTwinRecordingClient implements DigitalTwinRecordingClient {
    private final AppProperties props; private final WebClient web; private final Map<String,Instant> mockStarted=new ConcurrentHashMap<>();
    public DefaultDigitalTwinRecordingClient(AppProperties p,WebClient.Builder b){props=p;web=b.build();}
    public String request(AlertEvent a){
        if(mock()){String id="mock-recording-"+a.id();mockStarted.put(id,Instant.now());return id;}
        var body=Map.of("alertId",a.id(),"stationCode",a.stationCode(),"stationName",a.stationName(),"address",a.address(),"nx",a.nx(),"ny",a.ny(),"waterLevelMeters",a.waterLevelMeters(),"riskLevel",a.riskLevel().name(),"forecastRainfallMm",a.forecastRainfallMm());
        RecordingResponse r=web.post().uri(base()+"/api/recordings").bodyValue(body).retrieve().bodyToMono(RecordingResponse.class).block();
        if(r==null||r.recordingId()==null)throw new IllegalStateException("디지털 트윈이 recordingId를 반환하지 않았습니다.");return r.recordingId();
    }
    public RecordingStatus status(String id,Path destination){
        if(mock()){
            Instant started=mockStarted.get(id);if(started==null)return new RecordingStatus(RecordingStatus.State.FAILED,null,"알 수 없는 mock 녹화 ID");
            if(Instant.now().isBefore(started.plusMillis(props.getPipeline().getDigitalTwin().getMockCompletionDelayMs())))return new RecordingStatus(RecordingStatus.State.RUNNING,null,null);
            try{createMockVideo(destination);return new RecordingStatus(RecordingStatus.State.DONE,destination,null);}catch(Exception e){return new RecordingStatus(RecordingStatus.State.FAILED,null,e.getMessage());}
        }
        RecordingResponse r=web.get().uri(base()+"/api/recordings/{id}",id).retrieve().bodyToMono(RecordingResponse.class).block();
        if(r==null)return new RecordingStatus(RecordingStatus.State.FAILED,null,"빈 녹화 상태 응답");
        if("FAILED".equalsIgnoreCase(r.status()))return new RecordingStatus(RecordingStatus.State.FAILED,null,r.error());
        if(!"DONE".equalsIgnoreCase(r.status()))return new RecordingStatus(RecordingStatus.State.RUNNING,null,null);
        if(r.downloadUrl()==null)return new RecordingStatus(RecordingStatus.State.FAILED,null,"완료 응답에 downloadUrl이 없습니다.");
        try{Files.createDirectories(destination.getParent());DataBufferUtils.write(web.get().uri(resolve(r.downloadUrl())).retrieve().bodyToFlux(org.springframework.core.io.buffer.DataBuffer.class),destination).block();return new RecordingStatus(RecordingStatus.State.DONE,destination,null);}catch(Exception e){return new RecordingStatus(RecordingStatus.State.FAILED,null,e.getMessage());}
    }
    private void createMockVideo(Path target)throws Exception{if(Files.exists(target))return;Files.createDirectories(target.getParent());String configured=props.getPipeline().getDigitalTwin().getMockSourcePath();if(configured==null||configured.isBlank())throw new IllegalStateException("mock 입력 영상이 없습니다. DIGITAL_TWIN_MOCK_SOURCE에 MP4 경로를 지정하세요.");Path sample=Path.of(configured).toAbsolutePath().normalize();if(!Files.isRegularFile(sample))throw new IllegalStateException("mock 입력 영상을 찾을 수 없습니다: "+sample);Files.copy(sample,target,StandardCopyOption.REPLACE_EXISTING);}
    private boolean mock(){return "mock".equalsIgnoreCase(props.getPipeline().getDigitalTwin().getMode());}private String base(){return props.getPipeline().getDigitalTwin().getBaseUrl().replaceAll("/$","");}private String resolve(String u){return u.startsWith("http")?u:base()+(u.startsWith("/")?u:"/"+u);}
    private record RecordingResponse(String recordingId,String status,String downloadUrl,String error){}
}
