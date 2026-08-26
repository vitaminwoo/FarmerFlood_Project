package kr.co.farmerflood.trigger.domain;
import java.time.Instant;
public record WaterLevelObservation(String stationCode,String stationName,double waterLevelMeters,RiskLevel riskLevel,Instant observedAt) {}
