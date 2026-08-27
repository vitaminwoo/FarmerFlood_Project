package kr.co.farmerflood.trigger.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import kr.co.farmerflood.trigger.persistence.FarmlandEntity;
import org.junit.jupiter.api.Test;

class FarmlandRecipientSelectorTests {
    @Test
    void selectsOnlyLatestFarmlandForEachUser() {
        var oldFarm = farm("farm-old", "user-1", "2026-08-01T00:00:00Z");
        var latestFarm = farm("farm-latest", "user-1", "2026-08-02T00:00:00Z");
        var otherUserFarm = farm("farm-other", "user-2", "2026-08-01T00:00:00Z");

        assertThat(FarmlandRecipientSelector.onePerUser(List.of(oldFarm, otherUserFarm, latestFarm)))
            .extracting(farm -> farm.id)
            .containsExactly("farm-latest", "farm-other");
    }

    private FarmlandEntity farm(String id, String userId, String createdAt) {
        var farm = new FarmlandEntity();
        farm.id = id;
        farm.userId = userId;
        farm.createdAt = Instant.parse(createdAt);
        return farm;
    }
}
