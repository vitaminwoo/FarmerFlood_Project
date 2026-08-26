package kr.co.farmerflood.trigger.domain;
import java.time.Instant; import java.util.List;
public record RainfallTimeline(int nx,int ny,int forecastHours,Instant issuedAt,double accumulatedMillimeters,List<HourlyRainfall> hourly) {}
