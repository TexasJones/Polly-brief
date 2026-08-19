name: Generate Polly Brief
on:
  schedule:
    - cron: '0 12 * * *'
  workflow_dispatch:
    inputs:
      test_mode:
        description: 'Test mode (no sending, no committing)?'
        required: true
        default: 'false'
        type: choice
        options:
          - 'false'
          - 'true'
      publish_only:
        description: 'Publish only (commit + publish to Pages, but do NOT send the email)?'
        required: true
        default: 'false'
        type: choice
        options:
          - 'false'
          - 'true'
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      # Default TEST_MODE to the workflow_dispatch input when present,
      # otherwise fall back to 'false' so scheduled runs will send by default.
      TEST_MODE: ${{ github.event.inputs.test_mode || 'false' }}
      # PUBLISH_ONLY lets a manual run commit + publish docs/briefs/ (so the
      # "View in browser" link can be verified end-to-end) WITHOUT sending
      # the email to the real list. Only meaningful when TEST_MODE is
      # 'false' -- if TEST_MODE is 'true', nothing is committed or sent
      # regardless of this value. Defaults to 'false' so scheduled runs are
      # unaffected: they always commit AND send, same as before.
      PUBLISH_ONLY: ${{ github.event.inputs.publish_only || 'false' }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install requests beautifulsoup4 feedparser
      - name: Generate the Brief
        run: python3 polly_brief/generate_brief.py --out polly_brief.html
      - name: Commit updated job snapshot and published brief
        if: ${{ env.TEST_MODE == 'false' }}
        run: |
          git config user.name "actions-user"
          git config user.email "actions@github.com"
          git add polly_brief/.state/seen_jobs.json docs/briefs/
          git diff --quiet --cached || git commit -m "Update seen jobs snapshot and publish brief"
          git push
      - name: List files (debug)
        run: |
          echo "Current directory:"
          pwd
          echo "Files here:"
          ls -la
      - name: Send via Brevo
        # Sends only on a real run where publish_only was NOT requested --
        # this is the one change from before: a manual run with
        # test_mode=false and publish_only=true will still commit
        # docs/briefs/ (so you can check the "View in browser" link works)
        # but will skip this step, so no email goes out.
        if: ${{ env.TEST_MODE == 'false' && env.PUBLISH_ONLY == 'false' }}
        env:
          BREVO_API_KEY: ${{ secrets.BREVO_API_KEY }}
          BREVO_LIST_ID: ${{ secrets.BREVO_LIST_ID }}
          BREVO_SENDER_EMAIL: ${{ secrets.BREVO_SENDER_EMAIL }}
          BREVO_SENDER_NAME: "The Polly Brief"
          MAILING_ADDRESS: ${{ secrets.MAILING_ADDRESS }}
        run: python3 polly_brief/send_brevo.py --html-file polly_brief.html
      - name: Upload preview (test mode)
        if: ${{ env.TEST_MODE == 'true' }}
        uses: actions/upload-artifact@v4
        with:
          name: brief-preview
          path: polly_brief.html
          retention-days: 1
