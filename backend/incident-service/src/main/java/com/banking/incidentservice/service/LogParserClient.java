package com.banking.incidentservice.service;

import com.banking.incidentservice.dto.ParsedLogRequest;
import com.banking.incidentservice.dto.ParsedLogResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class LogParserClient {

    private final RestTemplate restTemplate;
    private final String parserBaseUrl;

    public LogParserClient(
            RestTemplateBuilder restTemplateBuilder,
            @Value("${log-parser.base-url:http://log-parser-service:5000}") String parserBaseUrl
    ) {
        this.restTemplate = restTemplateBuilder.build();
        this.parserBaseUrl = parserBaseUrl;
    }

    public ParsedLogResponse parse(ParsedLogRequest request) {
        ParsedLogResponse response = restTemplate.postForObject(
                parserBaseUrl + "/parse-log",
                request,
                ParsedLogResponse.class
        );

        if (response == null) {
            throw new IllegalStateException("Log parser service returned an empty response");
        }

        return response;
    }
}
