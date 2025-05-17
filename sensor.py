"""Sensor platform for the Azimut Energy integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AzimutBatteryDataCoordinator
from .const import (
    ATTR_BATTERY_CURRENT,
    ATTR_BATTERY_POWER,
    ATTR_BATTERY_AC_POWER,
    ATTR_BATTERY_EFFICIENCY,
    ATTR_BATTERY_SOC,
    ATTR_BATTERY_TEMPERATURE,
    ATTR_BATTERY_VOLTAGE,
    ATTR_ENERGY_TO_BATTERY,
    ATTR_ENERGY_FROM_BATTERY,
    DOMAIN,
    ICON_BATTERY,
    ICON_CURRENT,
    ICON_ENERGY,
    ICON_POWER,
    ICON_TEMPERATURE,
    ICON_VOLTAGE,
    ICON_EFFICIENCY,
)

SENSOR_TYPES = [
    SensorEntityDescription(
        key=ATTR_BATTERY_VOLTAGE,
        name="Battery DC Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_VOLTAGE,
    ),
    SensorEntityDescription(
        key=ATTR_BATTERY_CURRENT,
        name="Battery DC Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_CURRENT,
    ),
    SensorEntityDescription(
        key=ATTR_BATTERY_POWER,
        name="Battery DC Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_POWER,
    ),
    SensorEntityDescription(
        key=ATTR_BATTERY_AC_POWER,
        name="Battery AC Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_POWER,
    ),
    SensorEntityDescription(
        key=ATTR_BATTERY_EFFICIENCY,
        name="AC/DC Conversion Efficiency",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_EFFICIENCY,
    ),
    SensorEntityDescription(
        key=ATTR_BATTERY_SOC,
        name="Battery State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_BATTERY,
    ),
    SensorEntityDescription(
        key=ATTR_BATTERY_TEMPERATURE,
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_TEMPERATURE,
    ),
    SensorEntityDescription(
        key=ATTR_ENERGY_TO_BATTERY,
        name="Energy to Battery",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon=ICON_ENERGY,
    ),
    SensorEntityDescription(
        key=ATTR_ENERGY_FROM_BATTERY,
        name="Energy from Battery",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon=ICON_ENERGY,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the battery sensors from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Create a unique ID for the device
    device_unique_id = f"azimut_battery_{entry.entry_id}"
    
    entities = []
    
    # Create entities for each sensor type
    for description in SENSOR_TYPES:
        entities.append(
            AzimutBatterySensor(
                coordinator=coordinator,
                entity_description=description,
                device_unique_id=device_unique_id,
                entry_id=entry.entry_id,
            )
        )
    
    async_add_entities(entities)


class AzimutBatterySensor(CoordinatorEntity, SensorEntity):
    """Implementation of a battery sensor."""

    def __init__(
        self,
        coordinator: AzimutBatteryDataCoordinator,
        entity_description: SensorEntityDescription,
        device_unique_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._device_unique_id = device_unique_id
        self._entry_id = entry_id
        
        # Set unique ID for this entity
        self._attr_unique_id = f"{device_unique_id}_{entity_description.key}"
        
        # Set suggested display name
        self._attr_name = entity_description.name
        
        # Create device info (groups all entities under one device)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_unique_id)},
            name="Azimut Battery System",
            manufacturer="Azimut",
            model="Battery Monitor",
            sw_version="1.0.0",
            via_device=(DOMAIN, entry_id),
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
            
        # Get the key from the entity description
        key = self.entity_description.key
        
        # Get the value from the coordinator data
        return self.coordinator.data.get(key)
        
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None 