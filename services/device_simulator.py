"""Android Pixel 10 Pro device simulation service."""

import json
import random
import string
import uuid
from dataclasses import dataclass, field

import config

PIXEL_10_PRO_SPECS = {
    "width": 412,
    "height": 915,
    "device_width": 1080,
    "device_height": 2400,
    "pixel_ratio": 2.625,
    "color_depth": 24,
    "webgl_vendor": "Qualcomm",
    "webgl_renderer": "Adreno (TM) 750",
    "platform": "Linux armv8l",
    "vendor": "Google Inc.",
    "connection_type": "4g",
    "effective_type": "4g",
    "downlink": 10,
    "rtt": 120,
    "max_touch_points": 5,
    "device_memory": 12,
    "hardware_concurrency": 8,
}


def luhn_checksum(number: str) -> int:
    """Return the Luhn check digit for a numeric string."""
    digits = [int(digit) for digit in number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for digit in even_digits:
        total += sum(divmod(digit * 2, 10))
    return total % 10


def generate_imei() -> str:
    """Generate a syntactically valid IMEI (15 digits, Luhn-valid)."""
    tac = random.choice(["35847631", "35900012", "35250011", "86893003"])
    serial = "".join(random.choices(string.digits, k=15 - len(tac) - 1))
    partial = tac + serial
    check_digit = (10 - luhn_checksum(partial + "0")) % 10
    return partial + str(check_digit)


def generate_android_id() -> str:
    """Generate a 16-character hex Android ID."""
    return "".join(random.choices("0123456789abcdef", k=16))


def generate_device_fingerprint(model: str, build_id: str, android: str) -> str:
    """Return a realistic Android build fingerprint."""
    model_key = model.lower().replace(" ", "_")
    return (
        f"google/{model_key}/{model_key}:{android}/"
        f"{build_id}/eng.{random.randint(10000000, 99999999)}:user/release-keys"
    )


def random_chrome_patch() -> str:
    """Return installed Chrome version with small patch variation."""
    actual = config.CHROME_VERSION
    parts = actual.split(".")
    if len(parts) == 4:
        parts[3] = str(int(parts[3]) + random.randint(-5, 5))
        return ".".join(parts)
    return actual


def random_build_id() -> str:
    """Pick a realistic BUILD_ID from a pool of known Pixel 10 Pro builds."""
    builds = [
        "AP4A.250405.002",
        "AP4A.250305.001",
        "AP4A.250205.004",
        "AP3A.250105.002",
        "AP3A.241205.015",
    ]
    return random.choice(builds)


@dataclass
class DeviceProfile:
    imei: str
    android_id: str
    device_fingerprint: str
    user_agent: str
    chrome_version: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    model: str = config.DEVICE_MODEL
    brand: str = config.DEVICE_BRAND
    manufacturer: str = config.DEVICE_MANUFACTURER
    android_version: str = config.ANDROID_VERSION
    android_sdk: str = config.ANDROID_SDK
    build_id: str = config.BUILD_ID
    accept_language: str = config.DEVICE_ACCEPT_LANGUAGE
    locale: str = config.DEVICE_LOCALE
    timezone_id: str = config.EMULATION_TIMEZONE_ID
    geolocation_latitude: float = config.EMULATION_GEO_LATITUDE
    geolocation_longitude: float = config.EMULATION_GEO_LONGITUDE
    geolocation_accuracy: int = config.EMULATION_GEO_ACCURACY
    battery_level: float = field(default_factory=lambda: round(random.uniform(0.73, 0.96), 2))
    canvas_noise_blue: int = field(default_factory=lambda: random.randint(1, 3))

    def user_agent_brands(self) -> list[dict[str, str]]:
        """Return low-entropy UA brands for User-Agent Client Hints."""
        major = str(config.CHROME_MAJOR_VERSION)
        return [
            {"brand": "Chromium", "version": major},
            {"brand": "Google Chrome", "version": major},
            {"brand": "Not:A-Brand", "version": "24"},
        ]

    def user_agent_full_version_list(self) -> list[dict[str, str]]:
        """Return full version entries for User-Agent Client Hints."""
        return [
            {"brand": "Chromium", "version": self.chrome_version},
            {"brand": "Google Chrome", "version": self.chrome_version},
            {"brand": "Not:A-Brand", "version": "24.0.0.0"},
        ]

    def user_agent_metadata(self) -> dict[str, object]:
        """Return Chrome client-hints metadata for CDP override."""
        return {
            "brands": self.user_agent_brands(),
            "fullVersionList": self.user_agent_full_version_list(),
            "mobile": True,
            "platform": "Android",
            "platformVersion": f"{self.android_version}.0.0",
            "architecture": "",
            "bitness": "64",
            "model": self.model,
            "wow64": False,
        }

    def user_agent_high_entropy_values(self) -> dict[str, object]:
        """Return the JS payload exposed via navigator.userAgentData."""
        payload = dict(self.user_agent_metadata())
        payload["uaFullVersion"] = self.chrome_version
        return payload

    def client_hints_headers(self) -> dict:
        """Return User-Agent Client Hints headers for this device."""
        brands = ", ".join(
            f'"{item["brand"]}";v="{item["version"]}"'
            for item in self.user_agent_brands()
        )
        full_version_list = ", ".join(
            f'"{item["brand"]}";v="{item["version"]}"'
            for item in self.user_agent_full_version_list()
        )
        return {
            "Sec-CH-UA": brands,
            "Sec-CH-UA-Mobile": "?1",
            "Sec-CH-UA-Platform": '"Android"',
            "Sec-CH-UA-Platform-Version": f'"{self.android_version}.0.0"',
            "Sec-CH-UA-Model": f'"{self.model}"',
            "Sec-CH-UA-Full-Version": f'"{self.chrome_version}"',
            "Sec-CH-UA-Full-Version-List": full_version_list,
            "Sec-CH-UA-Arch": '""',
            "Sec-CH-UA-Bitness": '"64"',
        }

    def as_headers(self) -> dict:
        """Return extra HTTP headers that identify this device."""
        headers = {
            "Accept-Language": self.accept_language,
        }
        headers.update(self.client_hints_headers())
        return headers

    def navigator_overrides_js(self) -> str:
        """Return JavaScript to inject navigator/screen spoofs via CDP."""
        specs = PIXEL_10_PRO_SPECS
        brands_json = json.dumps(self.user_agent_brands())
        metadata_json = json.dumps(self.user_agent_high_entropy_values())
        locale_languages_json = json.dumps([self.locale, "en"])
        media_devices_json = json.dumps([
            {"deviceId": "default", "groupId": "g1", "kind": "audioinput", "label": ""},
            {"deviceId": "cam0", "groupId": "g2", "kind": "videoinput", "label": ""},
            {"deviceId": "cam1", "groupId": "g3", "kind": "videoinput", "label": ""},
            {"deviceId": "default", "groupId": "g4", "kind": "audiooutput", "label": ""},
        ])
        media_constraints_json = json.dumps({
            "deviceId": True,
            "facingMode": True,
            "frameRate": True,
            "height": True,
            "width": True,
        })
        return f"""
        (() => {{
            const defineGetter = (target, key, value) => {{
                try {{
                    Object.defineProperty(target, key, {{
                        get: () => value,
                        configurable: true,
                    }});
                }} catch (error) {{}}
            }};

            const defineValue = (target, key, value) => {{
                try {{
                    Object.defineProperty(target, key, {{
                        value,
                        configurable: true,
                    }});
                }} catch (error) {{}}
            }};

            const lowEntropyUaData = {{
                brands: {brands_json},
                mobile: true,
                platform: "Android",
            }};
            const highEntropyUaData = {metadata_json};

            defineGetter(navigator, "platform", {json.dumps(specs["platform"])});
            defineGetter(navigator, "vendor", {json.dumps(specs["vendor"])});
            defineGetter(navigator, "maxTouchPoints", {specs["max_touch_points"]});
            defineGetter(navigator, "hardwareConcurrency", {specs["hardware_concurrency"]});
            defineGetter(navigator, "deviceMemory", {specs["device_memory"]});
            defineGetter(navigator, "language", {json.dumps(self.locale)});
            defineGetter(navigator, "languages", {locale_languages_json});
            defineGetter(window, "devicePixelRatio", {specs["pixel_ratio"]});

            defineGetter(navigator, "userAgentData", {{
                ...lowEntropyUaData,
                getHighEntropyValues: async (hints) => {{
                    if (!Array.isArray(hints) || !hints.length) {{
                        return {{ ...highEntropyUaData }};
                    }}
                    return hints.reduce((acc, hint) => {{
                        if (hint in highEntropyUaData) {{
                            acc[hint] = highEntropyUaData[hint];
                        }}
                        return acc;
                    }}, {{}});
                }},
                toJSON: () => ({{ ...lowEntropyUaData }}),
            }});

            defineGetter(screen, "orientation", {{
                type: "portrait-primary",
                angle: 0,
                addEventListener: () => {{}},
                removeEventListener: () => {{}},
                dispatchEvent: () => true,
                onchange: null,
                lock: () => Promise.resolve(),
                unlock: () => {{}},
            }});

            defineValue(navigator, "vibrate", () => true);

            const mediaDevices = navigator.mediaDevices || {{}};
            mediaDevices.enumerateDevices = () => Promise.resolve({media_devices_json});
            mediaDevices.getSupportedConstraints = () => ({media_constraints_json});
            if (typeof mediaDevices.getUserMedia !== "function") {{
                mediaDevices.getUserMedia = () =>
                    Promise.reject(new DOMException("Permission denied", "NotAllowedError"));
            }}
            defineGetter(navigator, "mediaDevices", mediaDevices);

            const connection = navigator.connection || {{}};
            defineGetter(connection, "effectiveType", {json.dumps(specs["effective_type"])});
            defineGetter(connection, "type", "cellular");
            defineGetter(connection, "downlink", {specs["downlink"]});
            defineGetter(connection, "rtt", {specs["rtt"]});
            defineGetter(connection, "saveData", false);
            defineGetter(navigator, "connection", connection);

            defineGetter(screen, "width", {specs["width"]});
            defineGetter(screen, "height", {specs["height"]});
            defineGetter(screen, "availWidth", {specs["width"]});
            defineGetter(screen, "availHeight", {specs["height"]});
            defineGetter(screen, "colorDepth", {specs["color_depth"]});
            defineGetter(screen, "pixelDepth", {specs["color_depth"]});

            const webglDebugInfo = {{
                UNMASKED_VENDOR_WEBGL: 0x9245,
                UNMASKED_RENDERER_WEBGL: 0x9246,
            }};
            const patchWebGLContext = (ContextClass) => {{
                if (typeof ContextClass === "undefined" || !ContextClass.prototype) {{
                    return;
                }}

                const getParameterOrig = ContextClass.prototype.getParameter;
                const getExtensionOrig = ContextClass.prototype.getExtension;

                ContextClass.prototype.getParameter = function(param) {{
                    if (param === 0x9245) return {json.dumps(specs["webgl_vendor"])};
                    if (param === 0x9246) return {json.dumps(specs["webgl_renderer"])};
                    return getParameterOrig.call(this, param);
                }};

                ContextClass.prototype.getExtension = function(name) {{
                    if (name === "WEBGL_debug_renderer_info") {{
                        return webglDebugInfo;
                    }}
                    return getExtensionOrig ? getExtensionOrig.call(this, name) : null;
                }};
            }};

            patchWebGLContext(
                typeof WebGLRenderingContext === "undefined" ? undefined : WebGLRenderingContext
            );
            patchWebGLContext(
                typeof WebGL2RenderingContext === "undefined" ? undefined : WebGL2RenderingContext
            );

            defineGetter(navigator, "webdriver", undefined);

            const batteryManager = {{
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: {self.battery_level:.2f},
                addEventListener: () => {{}},
                removeEventListener: () => {{}},
                dispatchEvent: () => true,
                onchargingchange: null,
                onchargingtimechange: null,
                ondischargingtimechange: null,
                onlevelchange: null,
            }};
            defineValue(navigator, "getBattery", () => Promise.resolve(batteryManager));

            const origDateTimeFormat = Intl.DateTimeFormat;
            Intl.DateTimeFormat = function(locale, options) {{
                const nextOptions = {{ ...(options || {{}}) }};
                nextOptions.timeZone = nextOptions.timeZone || {json.dumps(self.timezone_id)};
                return new origDateTimeFormat(locale, nextOptions);
            }};
            Intl.DateTimeFormat.prototype = origDateTimeFormat.prototype;
            defineValue(Intl.DateTimeFormat, "supportedLocalesOf", origDateTimeFormat.supportedLocalesOf);

            if (typeof HTMLCanvasElement !== "undefined" && HTMLCanvasElement.prototype.toDataURL) {{
                const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {{
                    const ctx = this.getContext("2d");
                    if (ctx) {{
                        const style = ctx.fillStyle;
                        ctx.fillStyle = "rgba(0,0,{self.canvas_noise_blue},0.01)";
                        ctx.fillRect(0, 0, 1, 1);
                        ctx.fillStyle = style;
                    }}
                    return origToDataURL.apply(this, arguments);
                }};
            }}
        }})();
        """

    def summary(self) -> str:
        """Human-readable summary for Telegram messages."""
        return (
            f"📱 <b>Device Profile</b>\n"
            f"Model: {self.model}\n"
            f"Android: {self.android_version}\n"
            f"Build: {self.build_id}\n"
            f"Chrome: {self.chrome_version}\n"
            f"Session: <code>{self.session_id[:8]}…</code>"
        )


def create_device_profile() -> DeviceProfile:
    """Create a fresh Pixel 10 Pro device profile with unique identifiers."""
    build_id = random_build_id()
    chrome_version = random_chrome_patch()
    template = random.choice(config.USER_AGENT_TEMPLATES)
    user_agent = template.format(
        android=config.ANDROID_VERSION,
        model=config.DEVICE_MODEL,
        build=build_id,
        chrome=chrome_version,
    )
    fingerprint = generate_device_fingerprint(
        config.DEVICE_MODEL,
        build_id,
        config.ANDROID_VERSION,
    )
    return DeviceProfile(
        imei=generate_imei(),
        android_id=generate_android_id(),
        device_fingerprint=fingerprint,
        user_agent=user_agent,
        chrome_version=chrome_version,
        build_id=build_id,
    )


__all__ = ["DeviceProfile", "PIXEL_10_PRO_SPECS", "create_device_profile"]
