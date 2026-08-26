package kr.co.farmerflood.trigger.web;
import java.time.Instant;import java.util.Map;import java.util.NoSuchElementException;import org.springframework.http.*;import org.springframework.web.bind.annotation.*;
@RestControllerAdvice public class ApiExceptionHandler {
 @ExceptionHandler(NoSuchElementException.class)public ResponseEntity<Map<String,Object>> missing(NoSuchElementException e){return body(HttpStatus.NOT_FOUND,e.getMessage());}
 @ExceptionHandler({IllegalArgumentException.class,jakarta.validation.ValidationException.class})public ResponseEntity<Map<String,Object>> invalid(Exception e){return body(HttpStatus.BAD_REQUEST,e.getMessage());}
 @ExceptionHandler(SecurityException.class)public ResponseEntity<Map<String,Object>> unauthorized(SecurityException e){return body(HttpStatus.UNAUTHORIZED,e.getMessage());}
 private ResponseEntity<Map<String,Object>> body(HttpStatus s,String m){return ResponseEntity.status(s).body(Map.of("status",s.value(),"message",m==null?s.getReasonPhrase():m,"timestamp",Instant.now().toString()));}
}
