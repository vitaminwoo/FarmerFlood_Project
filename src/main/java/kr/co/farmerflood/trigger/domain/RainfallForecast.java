package kr.co.farmerflood.trigger.domain;
import java.time.Instant;
public record RainfallForecast(int nx,int ny,double accumulatedMillimeters,int forecastHours,Instant issuedAt) {}
