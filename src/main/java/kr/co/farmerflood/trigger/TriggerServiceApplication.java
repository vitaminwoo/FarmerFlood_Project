package kr.co.farmerflood.trigger;

import kr.co.farmerflood.trigger.config.AppProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.context.annotation.Bean;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.ExchangeStrategies;

@SpringBootApplication
@EnableScheduling
@EnableConfigurationProperties(AppProperties.class)
public class TriggerServiceApplication {

	@Bean
	WebClient.Builder webClientBuilder() {
		return WebClient.builder().exchangeStrategies(ExchangeStrategies.builder()
				.codecs(codecs -> codecs.defaultCodecs().maxInMemorySize(2 * 1024 * 1024))
				.build());
	}

	public static void main(String[] args) {
		SpringApplication.run(TriggerServiceApplication.class, args);
	}

}
