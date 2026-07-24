package com.banking.incidentservice.service;

import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@Service
public class AiEngineClient {

    private final RestTemplate restTemplate;
    private final String aiEngineBaseUrl;

    public AiEngineClient(
            RestTemplateBuilder restTemplateBuilder,
            @Value("${ai-engine.base-url:http://ai-engine:5000}") String aiEngineBaseUrl
    ) {
        this.restTemplate = restTemplateBuilder.build();
        this.aiEngineBaseUrl = aiEngineBaseUrl;
    }

    public void detectAnomaly(Long incidentId) {
        try {
            restTemplate.postForObject(
                    aiEngineBaseUrl + "/detect-anomaly",
                    Map.of("incidentId", incidentId),
                    Object.class
            );
        } catch (RestClientException exception) {
            throw new IllegalStateException("AI anomaly detection failed: " + exception.getMessage(), exception);
        }
    }
}
