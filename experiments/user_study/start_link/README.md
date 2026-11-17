# One shared study link

This small service assigns one of the four tool/pack orders, then redirects to the existing Google Form with the order filled in. Google Forms collects the participant's verified account email; there is no Participant ID question. The service does not collect email, submit responses or change the form. Python 3.12 is the only dependency.

## Behavior

- One shared `/study` URL for everyone. No participant chooses an order.
- New assignments go to a randomly chosen least-assigned sequence. Counts differ by at most one; this balances assignments, not completed responses.
- A random, secure, HTTP-only browser cookie retains the assignment for 90 days. Reopening in the same browser or two tabs returns the same order. Clearing cookies, using another device/private window, or sharing a browser changes this assumption.
- Plain GET/HEAD link previews do not allocate an ID. The page automatically posts after cookies are set. Without JavaScript, one Continue button performs the same action.
- The private SQLite ledger retains internal record numbers, sequence, creation time, and a hash of the random cookie token. These record numbers are not sent to the form. It contains no names, email addresses, IP addresses, or answers. Keep it out of Git and back it up with SQLite's backup API.
- Google Forms prefilled orders remain editable. The ledger has no email-to-assignment mapping; use the submitted order for response analysis and report deviations when known. Do not claim this locks the form or deduplicates participants across devices. Keep email-linked responses private and replace emails with anonymous analysis codes before sharing results.

## Configure

In the Form editor, choose **Get pre-filled link**. Select `KNIME A then Texera B` for Assigned sequence, leaving the other fields blank. Generate and save that URL in a local text file. This is not a response submission. Enable **Collect email addresses: Verified** in the form; do not add a separate email or ID question.

```sh
python configure.py prefilled-link.txt --origin https://YOUR_HOST:8080 --output start-link.json
python server.py --config /PRIVATE_CONFIG/start-link.json --database /PRIVATE_DATA/assignments.sqlite3 --port 18889
```

The server listens only on `127.0.0.1`. Place it behind HTTPS and proxy only `/study`, `/study/`, and `/study/start`. Preserve the existing Texera access gate for all other paths. The redirect destination comes only from the verified configuration, never from a request parameter. It never needs the study password, Google login credentials, or Texera API credentials.

Keep the service's `Referrer-Policy: same-origin` header: `no-referrer` makes an HTML form POST send a null Origin and fail the origin check. Its CSP permits the form's redirect to Google. The assignment cookie is parsed independently of unrelated cookies on the same host.

Suggested Caddy route, before the existing catch-all route:

```caddyfile
@studyStart path /study /study/ /study/start
handle @studyStart {
    reverse_proxy 127.0.0.1:18889
}
```

Add the service to the deployment's existing process supervisor. Keep the database across restarts/upgrades. When upgrading from the old two-field prefill, remove `id_field` from the service config; retain `order_field` and the entire ledger. Run the checks with a temporary database, not the participant ledger. Do not reset real assignments to rebalance an incomplete study.

## Verify before sharing

```sh
python -m unittest discover -s experiments/user_study/start_link -v
```

The tests cover concurrent balance, concurrent repeat visits, restart persistence, exact order-only prefill values for all four sequences, invalid configuration and requests, cookie failure, and nonallocating previews. They do not verify the current Google Form UI. Before sharing, check that the actual form shows the prefilled order and email collection notice, keeps the order on a repeat visit, and uses the intended UCI-owned form. Do not submit a response just to test the redirect.

This service has no ability to close/open responses, change questions, or retrieve responses. Existing study tasks and time limits stay the same.
