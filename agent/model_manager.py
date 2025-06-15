import os
import json
import yaml
import requests
from pathlib import Path
from google import genai
from dotenv import load_dotenv
from memory.tool_logger import get_tool_performance_stats
import time

load_dotenv()

ROOT = Path(__file__).parent.parent
MODELS_JSON = ROOT / "config" / "models.json"
PROFILE_YAML = ROOT / "config" / "profiles.yaml"

class ModelManager:
    def __init__(self):
        self.config = json.loads(MODELS_JSON.read_text())
        self.profile = yaml.safe_load(PROFILE_YAML.read_text())

        self.text_model_key = self.profile["llm"]["text_generation"]
        self.model_info = self.config["models"][self.text_model_key]
        self.model_type = self.model_info["type"]

        # Tool performance scores cache
        self.tool_scores = {}
        self.last_score_update = 0

        # ✅ Gemini initialization (your style)
        if self.model_type == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            self.client = genai.Client(api_key=api_key)

    async def generate_text(self, prompt: str) -> str:
        if self.model_type == "gemini":
            return self._gemini_generate(prompt)

        elif self.model_type == "ollama":
            return self._ollama_generate(prompt)

        raise NotImplementedError(f"Unsupported model type: {self.model_type}")

    def _gemini_generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_info["model"],
            contents=prompt
        )

        # ✅ Safely extract response text
        try:
            return response.text.strip()
        except AttributeError:
            try:
                return response.candidates[0].content.parts[0].text.strip()
            except Exception:
                return str(response)

    def _ollama_generate(self, prompt: str) -> str:
        response = requests.post(
            self.model_info["url"]["generate"],
            json={"model": self.model_info["model"], "prompt": prompt, "stream": False}
        )
        response.raise_for_status()
        return response.json()["response"].strip()
        
    def get_tool_scores(self, force_refresh=False):
        """
        Get tool performance scores based on logged metrics
        
        Args:
            force_refresh (bool): Force refreshing the scores from logs
            
        Returns:
            dict: Tool scores where higher is better
        """
        current_time = time.time()
        # Refresh scores every 5 minutes or if forced
        if force_refresh or not self.tool_scores or (current_time - self.last_score_update) > 300:
            stats = get_tool_performance_stats(days=7)
            
            self.tool_scores = {}
            for tool_name, tool_stats in stats.items():
                # Calculate a score based on success rate and latency
                if tool_stats["calls"] > 0:
                    success_rate = tool_stats["success_count"] / tool_stats["calls"]
                    # Normalize latency - lower is better (1.0 for latency <= 0.5s, 0.5 for latency >= 5s)
                    latency_score = max(0.5, min(1.0, 1.0 - (tool_stats["avg_latency"] - 0.5) / 9.0))
                    # Combined score (70% success rate, 30% latency)
                    self.tool_scores[tool_name] = (0.7 * success_rate) + (0.3 * latency_score)
                else:
                    # Default score for tools with no usage data
                    self.tool_scores[tool_name] = 0.5
                    
            self.last_score_update = current_time
            
        return self.tool_scores
        
    def adjust_tool_priority(self, tool_list):
        """
        Adjust the priority of tools based on their performance scores
        
        Args:
            tool_list (list): List of tool names to prioritize
            
        Returns:
            list: Prioritized list of tool names
        """
        scores = self.get_tool_scores()
        
        # Sort tools by their performance score (higher is better)
        scored_tools = [(tool, scores.get(tool, 0.5)) for tool in tool_list]
        scored_tools.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the tool names in priority order
        return [tool for tool, _ in scored_tools]
