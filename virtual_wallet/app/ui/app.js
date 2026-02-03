const api = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) {
      throw new Error(await res.text());
    }
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    return res.json();
  },
};

const $ = (id) => document.getElementById(id);

function setStats(stats) {
  $("stat-wallets").textContent = stats.wallets;
  $("stat-transactions").textContent = stats.transactions;
  $("stat-alerts").textContent = stats.alerts;
}

function renderWallets(wallets) {
  const container = $("wallets");
  container.innerHTML = "";
  wallets.slice(0, 8).forEach((wallet) => {
    const div = document.createElement("div");
    div.className = "list-item";
    div.innerHTML = `
      <strong>${wallet.wallet_id}</strong><br />
      Balance: ${wallet.balance.toFixed(2)} | Tag: ${wallet.tag}
    `;
    container.appendChild(div);
  });
}

function renderAlerts(alerts) {
  const container = $("alerts");
  container.innerHTML = "";
  alerts.forEach((alert) => {
    const div = document.createElement("div");
    div.className = "list-item alert";
    div.innerHTML = `
      <strong>${alert.level} (${alert.risk_score.toFixed(2)})</strong><br />
      Tx: ${alert.tx_id}<br />
      ${alert.message}
    `;
    container.appendChild(div);
  });
}

function renderTransactions(txs) {
  const container = $("transactions");
  container.innerHTML = "";
  txs.forEach((tx) => {
    const div = document.createElement("div");
    div.className = "list-item";
    div.innerHTML = `
      <strong>${tx.amount.toFixed(2)}</strong> | ${tx.risk_label}<br />
      From: ${tx.from_wallet} -> To: ${tx.to_wallet}<br />
      Score: ${tx.risk_score.toFixed(2)} | ${tx.reason}
    `;
    container.appendChild(div);
  });
}

async function refresh() {
  const [stats, wallets, alerts, transactions] = await Promise.all([
    api.get("/stats"),
    api.get("/api/wallets"),
    api.get("/api/alerts?limit=6"),
    api.get("/api/transactions?limit=10"),
  ]);
  setStats(stats);
  renderWallets(wallets.wallets || []);
  renderAlerts(alerts.alerts || []);
  renderTransactions(transactions.transactions || []);
}

$("btn-wallet").addEventListener("click", async () => {
  const payload = {
    wallet_id: $("wallet-id").value.trim() || null,
    balance: Number($("wallet-balance").value || 0),
    tag: $("wallet-tag").value,
  };
  const res = await api.post("/api/wallets", payload);
  $("wallet-id").value = "";
  $("tx-from").value = res.wallet.wallet_id;
  await refresh();
});

$("btn-seed").addEventListener("click", async () => {
  await api.post("/api/wallets/seed", { count: 6 });
  await refresh();
});

$("btn-tx").addEventListener("click", async () => {
  const payload = {
    from_wallet: $("tx-from").value.trim(),
    to_wallet: $("tx-to").value.trim(),
    amount: Number($("tx-amount").value || 0),
    policy: $("tx-policy").value,
  };
  if (!payload.from_wallet || !payload.to_wallet || payload.amount <= 0) return;
  await api.post("/api/transfer", payload);
  await refresh();
});

$("btn-sim").addEventListener("click", async () => {
  const payload = {
    count: Number($("sim-count").value || 50),
    profile: $("sim-profile").value,
    persist: $("sim-persist").value === "true",
  };
  const res = await api.post("/api/dataset/generate", {
    scenario: payload.profile,
    n: payload.count,
    persist: payload.persist,
  });
  if (res.file) {
    $("sim-download").href = `/api/dataset/download/${res.file}`;
  }
  await refresh();
});

refresh();
setInterval(refresh, 4000);
