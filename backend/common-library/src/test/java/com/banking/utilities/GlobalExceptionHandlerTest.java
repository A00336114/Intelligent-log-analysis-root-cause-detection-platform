package com.banking.utilities;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.banking.dto.ErrorResponse;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.context.request.WebRequest;

@ExtendWith(MockitoExtension.class)
class GlobalExceptionHandlerTest {

    @Mock
    private WebRequest request;

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void handleAllExceptionsBuildsInternalServerErrorResponse() {
        when(request.getDescription(false)).thenReturn("uri=/api/test");
        RuntimeException exception = new RuntimeException("boom");

        ResponseEntity<ErrorResponse> response = handler.handleAllExceptions(exception, request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
        assertThat(response.getBody()).isNotNull();
        assertThat(ReflectionTestUtils.getField(response.getBody(), "status")).isEqualTo(500);
        assertThat(ReflectionTestUtils.getField(response.getBody(), "error"))
                .isEqualTo("Internal Server Error");
        assertThat(ReflectionTestUtils.getField(response.getBody(), "message")).isEqualTo("boom");
        assertThat(ReflectionTestUtils.getField(response.getBody(), "path")).isEqualTo("uri=/api/test");
    }
}
