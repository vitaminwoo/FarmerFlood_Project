package kr.co.farmerflood.trigger.service;

import java.util.*;
import kr.co.farmerflood.trigger.persistence.*;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class VideoProductionJobRepository {
    private final VideoJobJpaRepository repository;
    private final AlertRepository alerts;
    public VideoProductionJobRepository(VideoJobJpaRepository repository,AlertRepository alerts){this.repository=repository;this.alerts=alerts;}
    @Transactional public VideoProductionJob save(VideoProductionJob j){VideoJobEntity e=new VideoJobEntity();e.id=j.getId();e.alertId=j.getAlert().id();e.storageName=j.getStorageName();e.status=j.getStatus().name();e.workerJobId=j.getWorkerJobId();e.currentStage=j.getCurrentStage();e.finalVideoPath=j.getFinalVideoPath();e.mediaUrl=j.getMediaUrl();e.message=j.getMessage();e.error=j.getError();e.progress=j.getProgress();e.createdAt=j.getCreatedAt();e.updatedAt=j.getUpdatedAt();repository.save(e);return j;}
    public VideoProductionJob find(String id){return repository.findById(id).map(this::domain).orElse(null);}
    public List<VideoProductionJob> findAll(){return repository.findAllByOrderByCreatedAtDesc().stream().map(this::domain).filter(Objects::nonNull).toList();}
    public List<VideoProductionJob> active(){return repository.findByStatusNotIn(List.of("COMPLETED","FAILED")).stream().map(this::domain).filter(Objects::nonNull).toList();}
    private VideoProductionJob domain(VideoJobEntity e){var alert=alerts.find(e.alertId);if(alert==null)return null;return new VideoProductionJob(e.id,e.storageName,alert,e.createdAt,e.updatedAt,VideoProductionJob.Status.valueOf(e.status),e.workerJobId,e.currentStage,e.finalVideoPath,e.mediaUrl,e.message,e.error,e.progress);}
}
