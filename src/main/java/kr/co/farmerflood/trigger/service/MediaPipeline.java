package kr.co.farmerflood.trigger.service;
import kr.co.farmerflood.trigger.domain.AlertEvent;
public interface MediaPipeline { void request(AlertEvent event); }
