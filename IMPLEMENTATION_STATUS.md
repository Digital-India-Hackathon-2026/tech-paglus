# Vision analyzer implementation status

## Implemented and tested

- Existing Next.js/FastAPI architecture preserved.
- Multi-image session API and mobile-first scanner UI.
- Image-content validation, EXIF correction, metadata stripping, blur/light/resolution checks.
- Configurable model registry and independently replaceable model adapters.
- Explicit unknown/development mode when weights are absent.
- Pest boxes and segmentation annotations when corresponding adapters return evidence.
- Segmentation-based severity with image-only disclaimer.
- Verified-treatment gate and configurable recommendation knowledge-base schema.
- Vision database migration, retention, history and feedback.
- Separate training/evaluation/export workspace.
- Backend automated test suite: 15 tests passing.
- Source-level JSX parsing completed for the scanner and home page.
- Farmer-friendly HTML report plus technical JSON export.
- Explicit apparently-healthy and unsupported/non-plant handling.

## Required before a production claim

- Licensed, representative datasets and documented provenance.
- Expert-reviewed crop, disease, pest, nutrient, damage and post-harvest labels.
- Trained and calibrated weights for every enabled model.
- Held-out field evaluation across devices, regions, growth stages and crops.
- Verified region-specific treatment records from official sources.
- Full frontend dependency install, production build and browser tests in the deployment environment.
- Load, security, privacy and retention-policy review.

The feature must remain labelled development mode until these requirements are completed.

## Verification limitation in this packaging environment

The npm registry was not reachable, so `npm ci`, `next build`, and Playwright could not be completed here. The source parses successfully, but the included README requires a clean frontend install, production build and browser run on the target Mac before release.
