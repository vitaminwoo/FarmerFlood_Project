package kr.co.farmerflood.trigger.service;
import java.time.Instant; import kr.co.farmerflood.trigger.domain.RiskLevel;
public record TriggerState(String locationId,Phase phase,RiskLevel riskLevel,double waterLevelMeters,Double forecastRainfallMm,String alertId,String lastError,Instant updatedAt){public enum Phase{NORMAL,ARMED,FIRED}public static TriggerState initial(String id){return new TriggerState(id,Phase.NORMAL,RiskLevel.NORMAL,0,null,null,null,Instant.now());}}
