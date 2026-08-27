package kr.co.farmerflood.trigger.provider.live;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import kr.co.farmerflood.trigger.config.AppProperties;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;

class HrfcoWaterLevelProviderTests {
    private HttpServer server;

    @AfterEach
    void stopServer() {
        if (server != null) server.stop(0);
    }

    @Test
    void usesOneCachedBulkRequestForMultipleSubscribersAndSelectsLatestReading() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/test-key/waterlevel/list/10M.json", exchange -> {
            calls.incrementAndGet();
            byte[] body = """
                {"code":"200","content":[
                  {"wlobscd":"3007610","ymdhm":"202608280550","wl":"1.20"},
                  {"wlobscd":"3011685","ymdhm":"202608280600","wl":"1.10"},
                  {"wlobscd":"3007610","ymdhm":"202608280600","wl":"1.45"}
                ]}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.start();

        AppProperties properties = new AppProperties();
        properties.getHrfco().setApiKey("test-key");
        properties.getHrfco().setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        HrfcoWaterLevelProvider provider = new HrfcoWaterLevelProvider(properties, WebClient.builder());

        assertThat(provider.latest(location("farm-1", "3007610")).waterLevelMeters()).isEqualTo(1.45);
        assertThat(provider.latest(location("farm-2", "3007610")).waterLevelMeters()).isEqualTo(1.45);
        assertThat(calls).hasValue(1);
    }

    private AppProperties.Location location(String id, String station) {
        AppProperties.Location location = new AppProperties.Location();
        location.setId(id); location.setName(id); location.setStationCode(station); location.setStationName("보은군(산성교)");
        AppProperties.Thresholds thresholds = new AppProperties.Thresholds();
        thresholds.setAttention(1.0); thresholds.setCaution(2.0); thresholds.setAlert(3.0); thresholds.setSerious(4.0);
        location.setThresholds(thresholds);
        return location;
    }
}
