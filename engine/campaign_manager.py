from engine.campaign_types import CampaignType
from engine.analysis_options import AnalysisType


class CampaignManager:

    def __init__(self):

        self.campaign_type = None
        self.analysis_type = None

    def select_campaign(self):

        print("\n========== Campaign Type ==========\n")

        print("1. Lead Generation")
        print("2. Display")
        print("3. CTV")
        print("4. Audio")
        print("5. Auto Detect")

        choice = input("\nSelect Campaign: ")

        mapping = {
            "1": CampaignType.LEAD_GENERATION,
            "2": CampaignType.DISPLAY,
            "3": CampaignType.CTV,
            "4": CampaignType.AUDIO,
            "5": CampaignType.AUTO_DETECT,
        }

        self.campaign_type = mapping.get(
            choice,
            CampaignType.AUTO_DETECT
        )

    def select_analysis(self):

        print("\n========== Analysis Type ==========\n")

        print("1. Full Campaign")
        print("2. Month over Month")
        print("3. Quarter over Quarter")
        print("4. Custom Date Range")

        choice = input("\nSelect Analysis: ")

        mapping = {
            "1": AnalysisType.FULL_CAMPAIGN,
            "2": AnalysisType.MONTH_OVER_MONTH,
            "3": AnalysisType.QUARTER_OVER_QUARTER,
            "4": AnalysisType.CUSTOM_DATE_RANGE,
        }

        self.analysis_type = mapping.get(
            choice,
            AnalysisType.FULL_CAMPAIGN
        )

    def summary(self):

        return {
            "campaign_type": self.campaign_type.value,
            "analysis_type": self.analysis_type.value,
        }