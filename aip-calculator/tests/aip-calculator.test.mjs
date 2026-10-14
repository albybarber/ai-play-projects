import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const browser = process.env.BROWSER_PATH ||
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

test('AIP calculator in a real browser', { timeout: 60000 }, async (t) => {
    const profile = await mkdtemp(path.join(root, '.aip-browser-test-'));
    const child = spawn(browser, [
        '--headless',
        '--no-first-run',
        '--no-default-browser-check',
        '--remote-debugging-port=0',
        `--user-data-dir=${profile}`,
        'about:blank'
    ], { env: { ...process.env, TMPDIR: profile }, stdio: ['ignore', 'ignore', 'pipe'] });
    let socket;
    try {
        const endpoint = await new Promise((resolve, reject) => {
            let output = '';
            const timeout = setTimeout(() => reject(new Error('Browser startup timed out')), 15000);
            child.once('error', (error) => {
                clearTimeout(timeout);
                reject(error);
            });
            child.once('exit', (code) => {
                clearTimeout(timeout);
                reject(new Error(`Browser exited (${code}): ${output}`));
            });
            child.stderr.on('data', (data) => {
                output += data;
                const match = output.match(/DevTools listening on (ws:\/\/\S+)/);
                if (match) {
                    clearTimeout(timeout);
                    resolve(match[1]);
                }
            });
        });
        const address = new URL(endpoint);
        const pages = await (await fetch(`http://${address.host}/json/list`)).json();
        socket = new WebSocket(pages.find((page) => page.type === 'page').webSocketDebuggerUrl);
        await new Promise((resolve, reject) => {
            socket.addEventListener('open', resolve, { once: true });
            socket.addEventListener('error', reject, { once: true });
        });
        let id = 0;
        const pending = new Map();
        socket.addEventListener('message', ({ data }) => {
            const message = JSON.parse(data);
            if (!pending.has(message.id)) return;
            const { resolve, reject } = pending.get(message.id);
            pending.delete(message.id);
            if (message.error) reject(new Error(JSON.stringify(message.error)));
            else resolve(message.result);
        });
        const command = (method, params = {}) => new Promise((resolve, reject) => {
            pending.set(++id, { resolve, reject });
            socket.send(JSON.stringify({ id, method, params }));
        });
        const evaluate = async (expression) => {
            const result = await command('Runtime.evaluate', { expression, returnByValue: true });
            assert.equal(result.exceptionDetails, undefined, JSON.stringify(result.exceptionDetails));
            return result.result.value;
        };
        await command('Page.navigate', {
            url: pathToFileURL(path.join(root, 'aip-calculator.html')).href
        });
        for (let attempt = 0; attempt < 100; attempt++) {
            if (await evaluate("!!document.getElementById('aipForm')")) break;
            await new Promise((resolve) => setTimeout(resolve, 50));
        }
        await evaluate(`window.setInput = (id, value) => {
            const input = document.getElementById(id);
            input.value = value;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        };
        window.snapshot = () => ({
            checked: document.getElementById('fullFiscalYear').checked,
            disabled: document.getElementById('startDate').disabled,
            startDate: document.getElementById('startDate').value,
            min: document.getElementById('startDate').min,
            max: document.getElementById('startDate').max,
            valid: document.getElementById('aipForm').checkValidity(),
            shown: document.getElementById('results').classList.contains('show'),
            basis: document.getElementById('calculationBasis').textContent,
            days: document.getElementById('daysWorked').textContent,
            proration: document.getElementById('proration').textContent,
            target: document.getElementById('fullYearTarget').textContent,
            prorated: document.getElementById('proratedTarget').textContent,
            payout: document.getElementById('finalPayout').textContent,
            period: document.getElementById('periodDisplay').textContent
        });
        setInput('salary', '100000');
        setInput('aipTarget', '10');
        setInput('corporateFactor', '120');
        setInput('individualFactor', '80');`);

        await t.test('unchecked default retains inclusive partial-year calculation', async () => {
            const result = await evaluate(`setInput('startDate', '2026-06-01');
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            const days = (Date.parse('2026-11-27') - Date.parse('2026-06-01')) / 86400000 + 1;
            const money = (value) => `$${value.toLocaleString('en-US', {
                minimumFractionDigits: 2, maximumFractionDigits: 2
            })}`;
            assert.equal(result.checked, false);
            assert.equal(result.disabled, false);
            assert.equal(result.shown, true);
            assert.equal(result.basis, 'Start-date proration');
            assert.equal(result.days, `${days} days (of 364)`);
            assert.equal(result.proration, `${(days / 364 * 100).toFixed(2)}%`);
            assert.equal(result.target, '$10,000.00');
            assert.equal(result.prorated, money(10000 * days / 364));
            assert.equal(result.payout, money(10000 * (days / 364) * 1.2 * 0.8));
        });

        await t.test('checking preserves an existing date and applies unchanged factors', async () => {
            const result = await evaluate(`document.getElementById('fullFiscalYear').click();
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.disabled, true);
            assert.equal(result.startDate, '2026-06-01');
            assert.equal(result.basis, 'Full fiscal year (self-declared)');
            assert.equal(result.days, '364 days (of 364)');
            assert.equal(result.proration, '100.00%');
            assert.equal(result.target, '$10,000.00');
            assert.equal(result.prorated, '$10,000.00');
            assert.equal(result.payout, '$9,600.00');
        });

        await t.test('unchecking restores the retained partial-year date and result', async () => {
            const result = await evaluate(`document.getElementById('fullFiscalYear').click();
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.disabled, false);
            assert.equal(result.startDate, '2026-06-01');
            assert.equal(result.valid, true);
            assert.equal(result.basis, 'Start-date proration');
            assert.notEqual(result.proration, '100.00%');
        });

        await t.test('a missing start date blocks only unchecked calculation', async () => {
            let result = await evaluate(`setInput('startDate', '');
                document.getElementById('results').classList.remove('show');
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.valid, false);
            assert.equal(result.shown, false);
            result = await evaluate(`document.getElementById('fullFiscalYear').click();
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.startDate, '');
            assert.equal(result.valid, true);
            assert.equal(result.shown, true);
            assert.equal(result.proration, '100.00%');
            assert.equal(result.payout, '$9,600.00');
            result = await evaluate(`document.getElementById('fullFiscalYear').click();
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.startDate, '');
            assert.equal(result.disabled, false);
            assert.equal(result.valid, false);
            assert.equal(result.shown, false);
            await evaluate("document.getElementById('fullFiscalYear').click();");
        });

        await t.test('reversed and missing fiscal dates block full-year calculation', async () => {
            for (const end of ['2025-11-28', '']) {
                const result = await evaluate(`setInput('fyEnd', '${end}');
                    document.getElementById('aipForm').requestSubmit(); snapshot();`);
                assert.equal(result.valid, false);
                assert.equal(result.shown, false);
                assert.equal(result.period, 'Enter a valid fiscal year range.');
            }
        });

        await t.test('fiscal edits use inclusive full-year days and update retained date bounds', async () => {
            let result = await evaluate(`setInput('startDate', '2026-06-01');
                setInput('fyStart', '2027-01-01'); setInput('fyEnd', '2027-12-31');
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.valid, true);
            assert.equal(result.days, '365 days (of 365)');
            assert.equal(result.proration, '100.00%');
            assert.equal(result.payout, '$9,600.00');
            assert.equal(result.min, '2027-01-01');
            assert.equal(result.max, '2027-12-31');
            result = await evaluate(`document.getElementById('fullFiscalYear').click();
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.startDate, '2026-06-01');
            assert.equal(result.disabled, false);
            assert.equal(result.valid, false);
            assert.equal(result.shown, false);
            result = await evaluate(`setInput('fyStart', '2025-11-29');
                setInput('fyEnd', '2026-11-27');
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.valid, true);
            assert.equal(result.shown, true);
            assert.equal(result.basis, 'Start-date proration');
        });

        await t.test('one-day fiscal ranges work and unchecked reversed ranges remain invalid', async () => {
            let result = await evaluate(`document.getElementById('fullFiscalYear').click();
                setInput('fyStart', '2026-06-01'); setInput('fyEnd', '2026-06-01');
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.days, '1 days (of 1)');
            assert.equal(result.proration, '100.00%');
            result = await evaluate(`document.getElementById('fullFiscalYear').click();
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.valid, true);
            assert.equal(result.proration, '100.00%');
            result = await evaluate(`setInput('fyEnd', '2026-05-31');
                document.getElementById('aipForm').requestSubmit(); snapshot();`);
            assert.equal(result.valid, false);
            assert.equal(result.shown, false);
        });
    } finally {
        socket?.close();
        if (child.pid && child.exitCode === null && child.signalCode === null) {
            const exited = new Promise((resolve) => child.once('exit', resolve));
            child.kill();
            await exited;
        }
        await rm(profile, { recursive: true, force: true });
    }
});
