package kr.co.farmerflood.trigger.service;
import java.nio.file.Path;import kr.co.farmerflood.trigger.domain.AlertEvent;
public interface DigitalTwinRecordingClient {String request(AlertEvent alert);RecordingStatus status(String externalId,Path destination);record RecordingStatus(State state,Path localFile,String error){public enum State{RUNNING,DONE,FAILED}}}
