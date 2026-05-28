---
tags: [dogfight, WEZ, weapon, damage]
created: 2026-05-26
---

# 🎯 WEZ 모델 (Weapon Engagement Zone)

[[00 - 전체 인덱스|← 인덱스로]]

---

## WEZ 정의

WEZ는 항공기가 적기에게 유효한 피해를 줄 수 있는 **공간적 영역**입니다.

```
         ← max_range_m (914m, ~3000ft) →
    [ WEZ 유효 구역 ]
    ←→ min_range_m (152m, ~500ft)

각도: ATA ≤ angle_deg/2 = 1.0°
```

## 기본 설정값

```python
wez = {
    "angle_deg":   2.0,                      # 반각 = 1.0°
    "min_range_m": 500 * 0.30480,  # ≈ 152m (500ft)
    "max_range_m": 3000 * 0.30480, # ≈ 914m (3000ft)
}
```

> ==데미지 발생 조건: ATA ≤ 1° AND 152m ≤ 거리 ≤ 914m 동시 충족. Pursuit Shaping 기준(30°)과 29° 차이가 있으므로 보상 설계 시 이 갭을 메워야 함.==

---

## 데미지 계산 공식

```python
base_range = max_range - min_range  # ≈ 762m

# 매 시뮬 스텝(1/60초)마다 평가
if min_range <= distance <= max_range:

    # 아군이 적기 WEZ 내 → 적기에게 피해
    if |ownship_ATA| <= angle_deg/2:
        target_damage = ((max_range - distance) / base_range) * delta_t

    # 적기가 아군 WEZ 내 → 아군에게 피해
    if |target_ATA| <= angle_deg/2:
        ownship_damage = ((max_range - distance) / base_range) * delta_t
```

### 데미지 함수 특성

| 거리 | 데미지 (per step at 60Hz) |
|------|--------------------------|
| min_range (152m) | max: base_range/base_range × 1/60 ≈ 0.0167 |
| mid_range (533m) | mid: 0.5 × 1/60 ≈ 0.0083 |
| max_range (914m) | 0 |

> **전략적 의미**: 가깝고 정면에 있을수록 높은 데미지 → **거리 유지 + 정렬(ATA 최소화)**

---

## WEZ 플래그 (in_wez)

```python
self._in_wez = target_damage > 0.0
# True = 아군이 현재 WEZ 안에서 적기에게 피해 중
```

관측 벡터 `tactical16[14]`에 반영:
```python
obs[14] = +1.0 if in_wez else -1.0
```

---

## WEZ 시각화

```
         아군 (Blue) 기수 방향 →
         
              [WEZ 원뿔]
              /   1°   \
             /___________\
         152m           914m
         
    ATA = Antenna Train Angle
    (아군 기수에서 적기까지의 각도)
    ATA ≤ 1° AND 152m ≤ dist ≤ 914m → 피해 발생
```

---

## 보상과의 연계

```python
# 데미지 차분이 보상의 핵심
r_damage = 20.0 * (target_damage - ownship_damage)

# Pursuit Shaping이 WEZ 진입을 유도
r_pursuit = 0.3 * ata_factor * range_factor
# → WEZ에 가까워질수록 ata_factor, range_factor 증가
```

---

## 관련 노트

- [[11 - 기하학 계산]] — ATA 계산 방법
- [[06 - 보상 함수]] — 데미지 기반 보상
- [[07 - 종료 조건]] — HEALTH=0 → 격추
- [[04 - 관측 공간]] — in_wez 피처
