package kr.co.farmerflood.trigger.service;
import java.nio.file.Path;
public interface AgentVideoClient {String submit(VideoProductionJob job,Path recording);AgentStatus status(String externalId,Path destination);record AgentStatus(State state,String message,Path localFile,String error){public enum State{RUNNING,DONE,FAILED}}}
