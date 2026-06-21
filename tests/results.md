## Stress Test Results (600 VUs)

### Environment

* Django + DRF
* PostgreSQL 17
* Redis 7
* Celery
* Docker Compose (WSL2)
* k6 load testing

### Load Profile

```javascript
stages: [
  { duration: '30s', target: 50 },
  { duration: '30s', target: 100 },
  { duration: '30s', target: 200 },
  { duration: '30s', target: 400 },
  { duration: '30s', target: 600 },
]
```

### Resource Usage During Test

#### ~60 VUs

| Service    | CPU  | Memory |
| ---------- | ---- | ------ |
| Web        | 51%  | 390 MB |
| Celery     | 26%  | 313 MB |
| PostgreSQL | 39%  | 29 MB  |
| Redis      | 1.4% | 4.7 MB |

#### ~130 VUs

| Service    | CPU  | Memory |
| ---------- | ---- | ------ |
| Web        | 110% | 484 MB |
| Celery     | 110% | 328 MB |
| PostgreSQL | 98%  | 32 MB  |
| Redis      | 2.9% | 5.7 MB |

#### ~230 VUs

| Service    | CPU  | Memory |
| ---------- | ---- | ------ |
| Web        | 138% | 510 MB |
| Celery     | 10%  | 356 MB |
| PostgreSQL | 31%  | 198 MB |
| Redis      | 0.8% | 6.1 MB |

#### ~430 VUs

| Service    | CPU  | Memory |
| ---------- | ---- | ------ |
| Web        | 131% | 585 MB |
| Celery     | 11%  | 376 MB |
| PostgreSQL | 29%  | 198 MB |
| Redis      | 1.1% | 6.6 MB |

### Failure Point

At approximately 550-600 VUs:

* Upload requests started timing out
* Status requests started timing out
* Result requests started timing out

Observed k6 errors:

```text
Post /jobs/upload/: request timeout
Get /jobs/{id}/status/: request timeout
Get /jobs/{id}/result/: request timeout
```

### Key Findings

1. No PostgreSQL connection exhaustion occurred.
2. No Redis bottleneck observed.
3. Memory usage remained stable.
4. Celery workers remained healthy.
5. Application remained functional up to several hundred concurrent users.
6. First failure mode was request timeout, not process crash.
7. Previous "too many clients already" issue was resolved.

### Conclusion

The system successfully handled hundreds of concurrent virtual users without database exhaustion or memory collapse.

The primary bottleneck appears to be request throughput at the Django application layer, where request latency eventually exceeded k6 timeout thresholds under sustained load approaching 600 VUs.
