"""
Builds the campaign story from analysis results.
"""


class CampaignContext:

    def __init__(self):

        self.headline = ""

        self.campaign_health = ""

        self.biggest_win = ""

        self.biggest_risk = ""

        self.primary_focus = ""

        self.best_asset = ""

        self.best_topic = ""

        self.trend = ""

    def to_dict(self):

        return {
            "headline": self.headline,
            "campaign_health": self.campaign_health,
            "biggest_win": self.biggest_win,
            "biggest_risk": self.biggest_risk,
            "primary_focus": self.primary_focus,
            "best_asset": self.best_asset,
            "best_topic": self.best_topic,
            "trend": self.trend,
        }