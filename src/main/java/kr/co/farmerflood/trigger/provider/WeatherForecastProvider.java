package kr.co.farmerflood.trigger.provider;
import kr.co.farmerflood.trigger.config.AppProperties; import kr.co.farmerflood.trigger.domain.*;
public interface WeatherForecastProvider {
    RainfallTimeline timeline(int nx,int ny,int hours);
    default RainfallForecast nextHours(AppProperties.Location location,int hours){
        var t=timeline(location.getNx(),location.getNy(),hours);
        return new RainfallForecast(t.nx(),t.ny(),t.accumulatedMillimeters(),t.forecastHours(),t.issuedAt());
    }
}
