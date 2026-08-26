package kr.co.farmerflood.trigger.domain;
import java.time.Instant;
public record AlertEvent(String id,String locationId,String locationName,String stationCode,String stationName,
                         String address,int nx,int ny,double waterLevelMeters,RiskLevel riskLevel,
                         double forecastRainfallMm,double rainfallThresholdMm,Instant triggeredAt,
                         String userId,String farmlandId,boolean productionRequested,String productionDecision) {}
