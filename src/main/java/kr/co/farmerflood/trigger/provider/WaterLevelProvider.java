package kr.co.farmerflood.trigger.provider;
import kr.co.farmerflood.trigger.config.AppProperties; import kr.co.farmerflood.trigger.domain.WaterLevelObservation;
public interface WaterLevelProvider { WaterLevelObservation latest(AppProperties.Location location); }
