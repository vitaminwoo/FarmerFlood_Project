package kr.co.farmerflood.trigger.domain;
import java.time.Instant;
public record StationSummary(String stationCode,String stationName,String address,double latitude,double longitude,
                             int nx,int ny,Double currentWaterLevel,Instant observedAt,String riskLevel,
                             WaterThresholds thresholds) {}
