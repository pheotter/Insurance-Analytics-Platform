select *
from values
    ('v1', 1, 1, 0),
    ('v2', 1, 0, 0),
    ('v3', 0, 0, 0)
as t(
    segmentation_version,
    use_state,
    use_risk_class,
    use_vehicle_segment
)
