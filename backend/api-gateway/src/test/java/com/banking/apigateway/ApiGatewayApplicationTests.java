package com.banking.apigateway;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.SpringBootApplication;

class ApiGatewayApplicationTests {

    @Test
    void applicationIsMarkedAsSpringBootApplication() {
        assertThat(ApiGatewayApplication.class.isAnnotationPresent(SpringBootApplication.class)).isTrue();
    }
}
