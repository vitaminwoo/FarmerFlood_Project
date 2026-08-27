package kr.co.farmerflood.trigger.provider.live;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import kr.co.farmerflood.trigger.config.AppProperties;
import kr.co.farmerflood.trigger.domain.WaterLevelObservation;
import kr.co.farmerflood.trigger.provider.RiskClassifier;
import kr.co.farmerflood.trigger.provider.WaterLevelProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import tools.jackson.databind.JsonNode;

@Component
@ConditionalOnProperty(name = "app.provider-mode", havingValue = "live")
public class HrfcoWaterLevelProvider implements WaterLevelProvider {
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyyMMddHHmm");
    private static final Duration FRESH_FOR = Duration.ofMinutes(1);
    private static final Duration STALE_FALLBACK_FOR = Duration.ofMinutes(30);

    private final AppProperties properties;
    private final WebClient client;
    private volatile ReadingCache cache;

    public HrfcoWaterLevelProvider(AppProperties properties, WebClient.Builder builder) {
        this.properties = properties;
        this.client = builder.baseUrl(properties.getHrfco().getBaseUrl()).build();
    }

    @Override
    public WaterLevelObservation latest(AppProperties.Location location) {
        if (properties.getHrfco().getApiKey().isBlank()) {
            throw new ProviderException("HRFCO", "HRFCO_API_KEY is missing");
        }
        JsonNode reading = readings().get(location.getStationCode());
        if (reading == null) {
            throw new ProviderException("HRFCO", "no water-level data for station=" + location.getStationCode());
        }
        double level = number(reading.path("wl"));
        if (!Double.isFinite(level)) {
            throw new ProviderException("HRFCO", "invalid water level for station=" + location.getStationCode());
        }
        return new WaterLevelObservation(
            location.getStationCode(), location.getStationName(), level,
            RiskClassifier.classify(level, location.getThresholds()),
            parse(reading.path("ymdhm").asText())
        );
    }

    private Map<String, JsonNode> readings() {
        ReadingCache current = cache;
        Instant now = Instant.now();
        if (current != null && current.loadedAt().isAfter(now.minus(FRESH_FOR))) return current.readings();
        synchronized (this) {
            current = cache;
            now = Instant.now();
            if (current != null && current.loadedAt().isAfter(now.minus(FRESH_FOR))) return current.readings();
            try {
                JsonNode body = client.get()
                    .uri("/{key}/waterlevel/list/10M.json", properties.getHrfco().getApiKey())
                    .retrieve().bodyToMono(JsonNode.class).block(Duration.ofSeconds(20));
                if (body == null || !body.path("content").isArray()) {
                    throw new ProviderException("HRFCO", body == null ? "empty response" : "code=" + body.path("code").asText());
                }
                Map<String, JsonNode> values = new HashMap<>();
                for (JsonNode item : body.path("content")) {
                    String station = item.path("wlobscd").asText().trim();
                    if (!station.isEmpty()) {
                        JsonNode previous = values.get(station);
                        if (previous == null || item.path("ymdhm").asText().compareTo(previous.path("ymdhm").asText()) > 0) {
                            values.put(station, item);
                        }
                    }
                }
                cache = new ReadingCache(now, Map.copyOf(values));
                return cache.readings();
            } catch (RuntimeException error) {
                if (current != null && current.loadedAt().isAfter(now.minus(STALE_FALLBACK_FOR))) return current.readings();
                throw error;
            }
        }
    }

    private double number(JsonNode node) {
        try { return Double.parseDouble(node.asText().trim()); }
        catch (RuntimeException error) { return Double.NaN; }
    }

    private Instant parse(String value) {
        try {
            String digits = value.replaceAll("[^0-9]", "");
            return LocalDateTime.parse(digits.substring(0, 12), TIME).atZone(ZoneId.of("Asia/Seoul")).toInstant();
        } catch (RuntimeException error) {
            return Instant.now();
        }
    }

    private record ReadingCache(Instant loadedAt, Map<String, JsonNode> readings) {}
}
