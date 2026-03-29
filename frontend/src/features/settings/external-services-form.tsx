import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { serviceConfigApi } from "../../api/service-config";
import type { ServiceConfigResponse, ServiceType } from "../../types/service-config";
import eyeIcon from "../../assets/icons/eye.svg";
import eyeClosedIcon from "../../assets/icons/eye-slash.svg";

const SERVICE_LABELS: Record<ServiceType, string> = {
  radarr: "Radarr",
  sonarr: "Sonarr",
  jellyfin: "Jellyfin",
};

const SERVICE_URL_PLACEHOLDERS: Record<ServiceType, string> = {
  radarr: "http://localhost:7878",
  sonarr: "http://localhost:8989",
  jellyfin: "http://localhost:8096",
};

type ConnectionStatus = "connected" | "error" | "idle";

interface FormErrors {
  url?: string;
  apiKey?: string;
  root?: string;
}

interface ServiceFormProps {
  config: ServiceConfigResponse;
}

function ServiceForm({ config }: ServiceFormProps) {
  const [url, setUrl] = useState(config.url);
  const [apiKey, setApiKey] = useState(config.masked_api_key);
  const [isTokenDirty, setIsTokenDirty] = useState(false);
  const [isConfigured, setIsConfigured] = useState(config.is_configured);
  const [showToken, setShowToken] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});

  const validateUrl = (val: string): string | undefined => {
    if (!val.trim()) return "URL is required";
    try {
      new URL(val);
    } catch {
      return "Must be a valid URL";
    }
  };

  const testMutation = useMutation({
    mutationFn: () =>
      serviceConfigApi.test(config.service_type, {
        url,
        ...(isTokenDirty ? { api_key: apiKey } : {}),
      }),
    onSuccess: (data) => {
      if (data.success) {
        setConnectionStatus("connected");
        setStatusMessage("Connected");
      } else {
        setConnectionStatus("error");
        setStatusMessage(data.message || "Connection failed");
      }
      setErrors((prev) => ({ ...prev, root: undefined }));
    },
    onError: () => {
      setConnectionStatus("error");
      setStatusMessage("Connection failed");
    },
  });

  const saveMutation = useMutation({
    mutationFn: () =>
      serviceConfigApi.upsert(config.service_type, {
        url,
        api_key: isTokenDirty ? apiKey : undefined,
      }),
    onSuccess: (data) => {
      setConnectionStatus("connected");
      setStatusMessage("Connected");
      setErrors({});
      setIsTokenDirty(false);
      setIsConfigured(true);
      setApiKey(data.masked_api_key);
    },
    onError: () => {
      setConnectionStatus("error");
      setStatusMessage("Save failed");
      setErrors({ root: "Failed to save. Check URL and API Token." });
    },
  });

  const handleTest = () => {
    const newErrors: FormErrors = {};

    const urlError = validateUrl(url);
    if (urlError) newErrors.url = urlError;

    if (!isConfigured && !isTokenDirty && !apiKey.trim()) {
      newErrors.apiKey = "API Token is required";
    } else if (isTokenDirty && !apiKey.trim()) {
      newErrors.apiKey = "API Token cannot be empty";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    testMutation.mutate();
  };

  const handleSave = () => {
    const newErrors: FormErrors = {};

    const urlError = validateUrl(url);
    if (urlError) newErrors.url = urlError;

    if (!isConfigured && !isTokenDirty && !apiKey.trim()) {
      newErrors.apiKey = "API Token is required";
    } else if (isTokenDirty && !apiKey.trim()) {
      newErrors.apiKey = "API Token cannot be empty";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    saveMutation.mutate();
  };

  const isTokenReadOnly = isConfigured && !isTokenDirty && !showToken;

  const label = SERVICE_LABELS[config.service_type];
  const placeholder = SERVICE_URL_PLACEHOLDERS[config.service_type];
  const isPending = testMutation.isPending || saveMutation.isPending;

  return (
    <div className="mb-8 pb-8 border-b border-[#c9b89a]/30 last:border-b-0 last:pb-0">
      <div className="flex items-center gap-2 mb-3" aria-live="polite">
        <h3 className="text-[#2a2520] font-medium">{label}</h3>
        {connectionStatus === "connected" && (
          <span className="flex items-center gap-1 text-green-600 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
            Connected
          </span>
        )}
        {connectionStatus === "error" && (
          <span className="flex items-center gap-1 text-red-500 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
            {statusMessage || "Disconnected"}
          </span>
        )}
      </div>

      <div className="flex flex-col md:flex-row md:items-start gap-1 md:gap-4 mb-4">
        <label
          htmlFor={`${config.service_type}-url`}
          className="text-[#2a2520] text-sm md:w-24 md:flex-shrink-0 md:pt-2.5"
        >
          URL
        </label>
        <div className="flex-1 min-w-0">
          <input
            id={`${config.service_type}-url`}
            type="text"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setErrors((prev) => ({ ...prev, url: undefined }));
            }}
            placeholder={placeholder}
            autoComplete="off"
            aria-invalid={!!errors.url}
            aria-describedby={errors.url ? `${config.service_type}-url-error` : undefined}
            className="w-full bg-white/80 border border-[#c9b89a] rounded-lg px-3 py-2.5 text-[#2a2520] placeholder-[#2a2520]/50 focus:border-mt-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none"
          />
          {errors.url && (
            <p id={`${config.service_type}-url-error`} className="text-red-400 text-xs mt-1">
              {errors.url}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-col md:flex-row md:items-start gap-1 md:gap-4 mb-4">
        <label
          htmlFor={`${config.service_type}-token`}
          className="text-[#2a2520] text-sm md:w-24 md:flex-shrink-0 md:pt-2.5"
        >
          API Token
        </label>
        <div className="flex-1 min-w-0">
          <div className="relative">
            <input
              id={`${config.service_type}-token`}
              type={showToken ? "text" : "password"}
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setIsTokenDirty(true);
                setErrors((prev) => ({ ...prev, apiKey: undefined }));
              }}
              readOnly={isTokenReadOnly}
              placeholder={isConfigured ? "" : "Enter API token"}
              autoComplete="new-password"
              aria-invalid={!!errors.apiKey}
              aria-describedby={errors.apiKey ? `${config.service_type}-token-error` : undefined}
              className={`w-full bg-white/80 border border-[#c9b89a] rounded-lg pl-3 pr-10 py-2.5 text-[#2a2520] placeholder-[#2a2520]/50 focus:border-mt-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none${isTokenReadOnly ? " cursor-default select-none" : ""}`}
            />
            <button
              type="button"
              onClick={() => setShowToken((v) => !v)}
              aria-label={showToken ? "Hide token" : "Show token"}
              className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none rounded"
            >
              <img
                src={showToken ? eyeIcon : eyeClosedIcon}
                alt=""
                aria-hidden="true"
                className="w-4 h-4 opacity-60"
              />
            </button>
          </div>
          {errors.apiKey && (
            <p id={`${config.service_type}-token-error`} className="text-red-400 text-xs mt-1">
              {errors.apiKey}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-col md:flex-row md:items-start gap-1 md:gap-4">
        <div className="hidden md:block md:w-24 md:flex-shrink-0" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          {errors.root && (
            <p role="alert" className="text-red-400 text-sm mb-2">
              {errors.root}
            </p>
          )}
          <p className="text-[#2a2520]/50 text-xs mb-3">
            URL used to connect to {label} server, including localhost, port, and access if required.
          </p>
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={handleTest}
              disabled={isPending}
              className="px-8 py-2 rounded-lg border border-[#c9b89a] text-[#2a2520] text-sm font-medium hover:bg-[#c9b89a]/20 disabled:opacity-50 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none"
            >
              {testMutation.isPending ? "Testing..." : "Test"}
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isPending}
              className="px-12 py-2 rounded-lg bg-mt-accent text-mt-black font-semibold text-sm hover:bg-mt-accent/90 disabled:opacity-50 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none"
            >
              {saveMutation.isPending ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ExternalServicesSection() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["service-configs"],
    queryFn: serviceConfigApi.list,
  });

  if (isLoading) {
    return <p className="text-[#2a2520]/60 text-sm">Loading configurations...</p>;
  }

  if (isError || !data) {
    return (
      <p role="alert" className="text-red-400 text-sm">
        Failed to load service configurations.
      </p>
    );
  }

  return (
    <div className="max-w-xl">
      {data.services.map((config) => (
        <ServiceForm key={config.service_type} config={config} />
      ))}
    </div>
  );
}
