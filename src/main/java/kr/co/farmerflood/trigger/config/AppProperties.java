package kr.co.farmerflood.trigger.config;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@Validated
@ConfigurationProperties(prefix = "app")
public class AppProperties {
    private String providerMode = "mock";
    private boolean pollingEnabled = true;
    private boolean mockAutoTriggerEnabled = false;
    @Positive private long pollDelayMs = 600_000;
    @Positive private double rainfallThresholdMm = 80;
    @Positive private int forecastHours = 24;
    @Valid private Remote hrfco = new Remote();
    @Valid private Remote kma = new Remote();
    @Valid private Pipeline pipeline = new Pipeline();
    @Valid private List<Location> locations = new ArrayList<>();
    public String getProviderMode() { return providerMode; } public void setProviderMode(String v) { providerMode = v; }
    public boolean isPollingEnabled() { return pollingEnabled; } public void setPollingEnabled(boolean v) { pollingEnabled = v; }
    public boolean isMockAutoTriggerEnabled() { return mockAutoTriggerEnabled; } public void setMockAutoTriggerEnabled(boolean v) { mockAutoTriggerEnabled = v; }
    public long getPollDelayMs() { return pollDelayMs; } public void setPollDelayMs(long v) { pollDelayMs = v; }
    public double getRainfallThresholdMm() { return rainfallThresholdMm; } public void setRainfallThresholdMm(double v) { rainfallThresholdMm = v; }
    public int getForecastHours() { return forecastHours; } public void setForecastHours(int v) { forecastHours = v; }
    public Remote getHrfco() { return hrfco; } public void setHrfco(Remote v) { hrfco = v; }
    public Remote getKma() { return kma; } public void setKma(Remote v) { kma = v; }
    public Pipeline getPipeline() { return pipeline; } public void setPipeline(Pipeline v) { pipeline = v; }
    public List<Location> getLocations() { return locations; } public void setLocations(List<Location> v) { locations = v; }
    public static class Remote {
        private String baseUrl = "", apiKey = "", serviceKey = "";
        public String getBaseUrl() { return baseUrl; } public void setBaseUrl(String v) { baseUrl = v; }
        public String getApiKey() { return apiKey; } public void setApiKey(String v) { apiKey = v; }
        public String getServiceKey() { return serviceKey; } public void setServiceKey(String v) { serviceKey = v; }
    }
    public static class Location {
        @NotBlank private String id, name, stationCode, stationName;
        private String ownerUserId;
        private int nx, ny; @Valid private Thresholds thresholds = new Thresholds();
        public String getId() { return id; } public void setId(String v) { id = v; }
        public String getName() { return name; } public void setName(String v) { name = v; }
        public String getStationCode() { return stationCode; } public void setStationCode(String v) { stationCode = v; }
        public String getStationName() { return stationName; } public void setStationName(String v) { stationName = v; }
        public String getOwnerUserId() { return ownerUserId; } public void setOwnerUserId(String v) { ownerUserId = v; }
        public int getNx() { return nx; } public void setNx(int v) { nx = v; }
        public int getNy() { return ny; } public void setNy(int v) { ny = v; }
        public Thresholds getThresholds() { return thresholds; } public void setThresholds(Thresholds v) { thresholds = v; }
    }
    public static class Thresholds {
        private double attention, caution, alert, serious;
        public double getAttention() { return attention; } public void setAttention(double v) { attention = v; }
        public double getCaution() { return caution; } public void setCaution(double v) { caution = v; }
        public double getAlert() { return alert; } public void setAlert(double v) { alert = v; }
        public double getSerious() { return serious; } public void setSerious(double v) { serious = v; }
    }
    public static class Pipeline {
        private boolean enabled = true;
        @NotBlank private String storageDir = "runtime/media";
        @Positive private long pollDelayMs = 1_000;
        @Valid private DigitalTwin digitalTwin = new DigitalTwin();
        @Valid private Agent agent = new Agent();
        @Valid private Worker worker = new Worker();
        public boolean isEnabled() { return enabled; } public void setEnabled(boolean v) { enabled = v; }
        public String getStorageDir() { return storageDir; } public void setStorageDir(String v) { storageDir = v; }
        public long getPollDelayMs() { return pollDelayMs; } public void setPollDelayMs(long v) { pollDelayMs = v; }
        public DigitalTwin getDigitalTwin() { return digitalTwin; } public void setDigitalTwin(DigitalTwin v) { digitalTwin = v; }
        public Agent getAgent() { return agent; } public void setAgent(Agent v) { agent = v; }
        public Worker getWorker() { return worker; } public void setWorker(Worker v) { worker = v; }
    }
    public static class DigitalTwin {
        @NotBlank private String mode = "mock", baseUrl = "http://localhost:3000"; private String mockSourcePath = "";
        @Positive private long mockCompletionDelayMs = 2_000;
        public String getMode() { return mode; } public void setMode(String v) { mode = v; }
        public String getBaseUrl() { return baseUrl; } public void setBaseUrl(String v) { baseUrl = v; }
        public String getMockSourcePath() { return mockSourcePath; } public void setMockSourcePath(String v) { mockSourcePath = v; }
        public long getMockCompletionDelayMs() { return mockCompletionDelayMs; } public void setMockCompletionDelayMs(long v) { mockCompletionDelayMs = v; }
    }
    public static class Agent {
        @NotBlank private String baseUrl = "http://127.0.0.1:8090", mode = "mock", farmerName = "농업인";
        public String getBaseUrl() { return baseUrl; } public void setBaseUrl(String v) { baseUrl = v; }
        public String getMode() { return mode; } public void setMode(String v) { mode = v; }
        public String getFarmerName() { return farmerName; } public void setFarmerName(String v) { farmerName = v; }
    }
    public static class Worker {
        @NotBlank private String baseUrl = "http://127.0.0.1:8091", farmerName = "농업인";
        private boolean autoStart = true;
        @NotBlank private String startCommand = "services/team-flood/run.sh";
        @Positive private long startupTimeoutMs = 15_000;
        public String getBaseUrl() { return baseUrl; } public void setBaseUrl(String v) { baseUrl = v; }
        public String getFarmerName() { return farmerName; } public void setFarmerName(String v) { farmerName = v; }
        public boolean isAutoStart() { return autoStart; } public void setAutoStart(boolean v) { autoStart = v; }
        public String getStartCommand() { return startCommand; } public void setStartCommand(String v) { startCommand = v; }
        public long getStartupTimeoutMs() { return startupTimeoutMs; } public void setStartupTimeoutMs(long v) { startupTimeoutMs = v; }
    }
}
