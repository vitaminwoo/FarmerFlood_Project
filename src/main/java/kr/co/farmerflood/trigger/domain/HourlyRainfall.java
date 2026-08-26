package kr.co.farmerflood.trigger.domain;
import java.time.Instant;
public record HourlyRainfall(Instant forecastAt,String rawValue,double millimeters) {}
