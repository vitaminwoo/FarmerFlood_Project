package kr.co.farmerflood.trigger.service;

import java.util.*;
import kr.co.farmerflood.trigger.config.AppProperties;
import kr.co.farmerflood.trigger.domain.StationSummary;
import kr.co.farmerflood.trigger.persistence.*;
import kr.co.farmerflood.trigger.provider.*;
import org.slf4j.*;
import org.springframework.stereotype.Service;

@Service
public class MonitoringTargetService {
    private static final Logger log = LoggerFactory.getLogger(MonitoringTargetService.class);
    private final AppProperties properties;
    private final FarmlandJpaRepository farmlands;
    private final FarmlandStationJpaRepository links;
    private final WaterStationCatalogue catalogue;

    public MonitoringTargetService(AppProperties properties, FarmlandJpaRepository farmlands,
                                   FarmlandStationJpaRepository links, WaterStationCatalogue catalogue) {
        this.properties = properties; this.farmlands = farmlands; this.links = links; this.catalogue = catalogue;
    }

    public List<AppProperties.Location> locations() {
        List<AppProperties.Location> result = new ArrayList<>(properties.getLocations());
        try {
            Map<String, StationSummary> stationMap = new HashMap<>();
            catalogue.chungbukStations().forEach(s -> stationMap.put(s.stationCode(), s));
            Map<String, FarmlandEntity> farmlandMap = new HashMap<>();
            farmlands.findByActiveTrue().forEach(f -> farmlandMap.put(f.id, f));
            for (var link : links.findByActiveTrueAndPriorityOrder(1)) {
                var farm = farmlandMap.get(link.farmlandId);
                var station = stationMap.get(link.stationCode);
                if (farm == null || station == null || !station.thresholds().complete()) continue;
                var grid = KmaGridConverter.from(farm.latitude, farm.longitude);
                AppProperties.Location location = new AppProperties.Location();
                location.setId(farm.id);
                location.setName(farm.name + " · " + farm.address);
                location.setOwnerUserId(farm.userId);
                location.setStationCode(station.stationCode());
                location.setStationName(station.stationName());
                location.setNx(grid.nx()); location.setNy(grid.ny());
                AppProperties.Thresholds thresholds = new AppProperties.Thresholds();
                thresholds.setAttention(station.thresholds().attention());
                thresholds.setCaution(station.thresholds().caution());
                thresholds.setAlert(station.thresholds().alert());
                thresholds.setSerious(station.thresholds().serious());
                location.setThresholds(thresholds);
                result.add(location);
            }
        } catch (RuntimeException error) {
            log.warn("Registered farmland monitoring targets could not be loaded: {}", error.getMessage());
        }
        return List.copyOf(result);
    }
}
