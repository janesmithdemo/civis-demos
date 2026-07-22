"""Simulate survey responses for a drawn sample.

There's no real survey vendor in this demo, so this module fabricates
plausible answers to two synthetic questions -- `vote_choice` and
`approval_rating` -- using the sample's modeled `likely_dem`/`likely_rep`
propensity scores as latent signal, plus simulated nonresponse. This stands
in for whatever response data a buyer's own survey vendor would supply.
"""
import numpy as np
import pandas as pd

CHOICES = ["Democrat", "Republican", "Undecided"]


def simulate_responses(sample_df, base_response_rate, random_seed=None):
    """Return a responses DataFrame (one row per person who "responded"),
    with columns [voterbase_id, vote_choice, approval_rating].
    """
    rng = np.random.default_rng(random_seed)

    responded_mask = rng.random(len(sample_df)) < base_response_rate
    responders = sample_df.loc[responded_mask].reset_index(drop=True)

    vote_choice = _simulate_vote_choice(responders, rng)
    approval_rating = _simulate_approval_rating(responders, rng)

    return pd.DataFrame(
        {
            "voterbase_id": responders["voterbase_id"].values,
            "vote_choice": vote_choice,
            "approval_rating": approval_rating,
        }
    )


def _simulate_vote_choice(responders, rng):
    dem = responders["likely_dem"].to_numpy()
    rep = responders["likely_rep"].to_numpy()
    undecided = np.clip(1 - dem - rep, 0.05, None)

    probs = np.stack([dem, rep, undecided], axis=1)
    probs = probs / probs.sum(axis=1, keepdims=True)

    return [rng.choice(CHOICES, p=row_probs) for row_probs in probs]


def _simulate_approval_rating(responders, rng):
    lean = responders["likely_dem"].to_numpy() - responders["likely_rep"].to_numpy()
    centered = 3 + lean * 1.5
    noisy = centered + rng.normal(0, 0.75, size=len(responders))
    return np.clip(np.round(noisy), 1, 5).astype(int)
