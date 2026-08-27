package kr.co.farmerflood.trigger.service;

import java.time.*;import java.time.format.DateTimeFormatter;
import kr.co.farmerflood.trigger.domain.AlertEvent;

public class VideoProductionJob {
    public enum Status { QUEUED, WORKFLOW_RUNNING, COMPLETED, FAILED }
    private final String id; private final String storageName; private final AlertEvent alert; private final Instant createdAt;
    private volatile Status status; private volatile String workerJobId, currentStage, finalVideoPath, mediaUrl, message, error; private volatile int progress, connectionAttempts;
    private volatile Instant updatedAt;
    public VideoProductionJob(AlertEvent alert) { id=alert.id();this.alert=alert;storageName=storageName(alert);createdAt=Instant.now();updatedAt=createdAt;status=Status.QUEUED;currentStage="queued";message="팀 디지털 트윈·Agent 작업 요청 대기"; }
    public VideoProductionJob(String id,String storageName,AlertEvent alert,Instant createdAt,Instant updatedAt,Status status,String workerJobId,String currentStage,String finalVideoPath,String mediaUrl,String message,String error,int progress){this.id=id;this.storageName=storageName;this.alert=alert;this.createdAt=createdAt;this.updatedAt=updatedAt;this.status=status;this.workerJobId=workerJobId;this.currentStage=currentStage;this.finalVideoPath=finalVideoPath;this.mediaUrl=mediaUrl;this.message=message;this.error=error;this.progress=progress;}
    private static String storageName(AlertEvent a){String station=a.stationName().replaceAll("[^가-힣A-Za-z0-9_-]","_").replaceAll("_+","_");String time=DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss").withZone(ZoneId.of("Asia/Seoul")).format(a.triggeredAt());String alertSuffix=a.id().replaceAll("[^A-Za-z0-9]","");alertSuffix=alertSuffix.substring(0,Math.min(8,alertSuffix.length()));return station+"_"+time+"_"+alertSuffix;}
    public synchronized void update(Status s,String m){status=s;message=m;updatedAt=Instant.now();}
    public synchronized void fail(Exception e){status=Status.FAILED;message="영상 제작 실패 ("+currentStage+")";error=e.getMessage();updatedAt=Instant.now();}
    public synchronized boolean waitForWorker(){connectionAttempts++;currentStage="worker_connect";message="팀 영상 Worker 연결 대기 ("+connectionAttempts+"/30)";error=null;updatedAt=Instant.now();return connectionAttempts<30;}
    public String getId(){return id;} public String getStorageName(){return storageName;} public AlertEvent getAlert(){return alert;} public Status getStatus(){return status;} public Instant getCreatedAt(){return createdAt;} public Instant getUpdatedAt(){return updatedAt;}
    public String getWorkerJobId(){return workerJobId;} public void setWorkerJobId(String v){workerJobId=v;}
    public String getCurrentStage(){return currentStage;} public void setCurrentStage(String v){currentStage=v;}
    public int getProgress(){return progress;} public void setProgress(int v){progress=v;}
    public String getFinalVideoPath(){return finalVideoPath;} public void setFinalVideoPath(String v){finalVideoPath=v;}
    public String getMediaUrl(){return mediaUrl;} public void setMediaUrl(String v){mediaUrl=v;}
    public String getMessage(){return message;} public String getError(){return error;}
}
