package kr.co.farmerflood.trigger.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import kr.co.farmerflood.trigger.domain.*;
import org.junit.jupiter.api.Test;

class VideoProductionJobTests {
    @Test
    void usesUniqueStorageForAlertsTriggeredInSameSecond() {
        Instant triggeredAt = Instant.parse("2026-08-27T12:28:31Z");
        var first = new VideoProductionJob(alert("aaaaaaaa-1111", triggeredAt));
        var second = new VideoProductionJob(alert("bbbbbbbb-2222", triggeredAt));

        assertThat(first.getStorageName()).isNotEqualTo(second.getStorageName());
        assertThat(first.getStorageName()).endsWith("_aaaaaaaa");
        assertThat(second.getStorageName()).endsWith("_bbbbbbbb");
    }

    private AlertEvent alert(String id, Instant triggeredAt) {
        return new AlertEvent(id,"location","location","MOCK-005","속리산면_mock_5","address",75,106,1.4,
            RiskLevel.ATTENTION,35,35,triggeredAt,"user","farm",true,"test");
    }
}
