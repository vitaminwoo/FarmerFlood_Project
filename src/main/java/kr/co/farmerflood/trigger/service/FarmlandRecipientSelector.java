package kr.co.farmerflood.trigger.service;

import java.time.Instant;
import java.util.*;
import kr.co.farmerflood.trigger.persistence.FarmlandEntity;

/** Selects one representative farmland per notification recipient. */
final class FarmlandRecipientSelector {
    private FarmlandRecipientSelector() {}

    static List<FarmlandEntity> onePerUser(Collection<FarmlandEntity> farmlands) {
        Map<String, FarmlandEntity> representatives = new LinkedHashMap<>();
        farmlands.stream()
            .filter(Objects::nonNull)
            .filter(farm -> farm.userId != null && !farm.userId.isBlank())
            .sorted(Comparator.comparing(
                (FarmlandEntity farm) -> Optional.ofNullable(farm.createdAt).orElse(Instant.EPOCH),
                Comparator.reverseOrder()
            ).thenComparing(farm -> farm.id, Comparator.nullsLast(String::compareTo)))
            .forEach(farm -> representatives.putIfAbsent(farm.userId, farm));
        return List.copyOf(representatives.values());
    }
}
