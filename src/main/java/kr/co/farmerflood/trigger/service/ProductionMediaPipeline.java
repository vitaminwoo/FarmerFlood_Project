package kr.co.farmerflood.trigger.service;

import java.nio.file.Path;import java.time.Instant;import kr.co.farmerflood.trigger.config.AppProperties;import kr.co.farmerflood.trigger.domain.AlertEvent;
import org.slf4j.Logger;import org.slf4j.LoggerFactory;import org.springframework.scheduling.annotation.Scheduled;import org.springframework.stereotype.Component;

@Component
public class ProductionMediaPipeline implements MediaPipeline {
    private static final Logger log=LoggerFactory.getLogger(ProductionMediaPipeline.class);
    private final AppProperties props;private final VideoProductionJobRepository jobs;private final FloodVideoWorkflowClient worker;private final WebNotificationGateway notifications;private final MobileAppService mobile;
    public ProductionMediaPipeline(AppProperties p,VideoProductionJobRepository j,FloodVideoWorkflowClient w,WebNotificationGateway n,MobileAppService mobile){props=p;jobs=j;worker=w;notifications=n;this.mobile=mobile;}
    public void request(AlertEvent event){if(!props.getPipeline().isEnabled()){log.info("Media pipeline disabled; alertId={}",event.id());return;}jobs.save(new VideoProductionJob(event));notifications.send(new NotificationMessage(event.id(),"경고 영상 제작 시작",event.locationName()+" 인근 침수 위험 영상 제작을 시작했습니다.",null,Instant.now()));}
    @Scheduled(fixedDelayString="${app.pipeline.poll-delay-ms:1000}")
    public void advance(){if(!props.getPipeline().isEnabled())return;for(VideoProductionJob j:jobs.active()){try{step(j);}catch(Exception e){if(j.getStatus()==VideoProductionJob.Status.QUEUED&&isConnectionFailure(e)&&j.waitForWorker()){log.info("Waiting for team flood worker; alertId={}",j.getId());}else{j.fail(e);log.warn("Video pipeline failed for alertId={}: {}",j.getId(),e.getMessage(),e);}}finally{jobs.save(j);}}}
    private void step(VideoProductionJob j){Path dir=Path.of(props.getPipeline().getStorageDir()).toAbsolutePath().normalize().resolve(j.getStorageName());switch(j.getStatus()){
        case QUEUED->{j.setWorkerJobId(worker.submit(j));j.setCurrentStage("queued");j.setProgress(1);j.update(VideoProductionJob.Status.WORKFLOW_RUNNING,"팀 디지털 트윈·멀티Agent 실행 중");}
        case WORKFLOW_RUNNING->{var s=worker.status(j.getWorkerJobId(),dir.resolve("final-warning.mp4"));j.setCurrentStage(s.stage());j.setProgress(s.progress());j.update(VideoProductionJob.Status.WORKFLOW_RUNNING,s.message());if(s.state()==FloodVideoWorkflowClient.State.FAILED)throw new IllegalStateException(s.error());if(s.state()==FloodVideoWorkflowClient.State.DONE){j.setFinalVideoPath(s.localFile().toString());j.setMediaUrl("/api/production-jobs/"+j.getId()+"/video");j.setCurrentStage("completed");j.setProgress(100);j.update(VideoProductionJob.Status.COMPLETED,"디지털 트윈·멀티Agent 경고 영상 제작 완료");notifyReady(j);}}
        default->{} }}
    private void notifyReady(VideoProductionJob j){AlertEvent e=j.getAlert();notifications.send(new NotificationMessage(e.id(),"경고 영상 제작 완료",e.locationName()+" 인근 침수 위험 경고 영상이 준비되었습니다.",j.getMediaUrl(),Instant.now()));mobile.publishReady(e,j.getMediaUrl());}
    private boolean isConnectionFailure(Throwable error){for(Throwable t=error;t!=null;t=t.getCause()){if(t instanceof java.net.ConnectException)return true;String message=t.getMessage();if(message!=null&&message.contains("Connection refused"))return true;}return false;}
}
