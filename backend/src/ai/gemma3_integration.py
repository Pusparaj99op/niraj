"""
Ollama Gemma3 Integration Client for NIRAJ Trading System

This module provides integration with Ollama's Gemma3 model for AI-powered trading analysis,
predictions, and market insights. It handles communication with the Ollama API, manages
model interactions, and provides specialized trading-focused AI capabilities.
"""

import json
import time
import asyncio
import aiohttp
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.config import get_config
from ..models.ai_model import AIModel, ModelType, LearningMode, ModelStatus
from ..models.ai_prediction import AIPrediction, PredictionType

# Configure structured logging
logger = structlog.get_logger(__name__)


class AnalysisType(str, Enum):
    """Types of analysis supported by Gemma3 integration"""
    MARKET_SENTIMENT = "market_sentiment"
    PRICE_PREDICTION = "price_prediction"
    TECHNICAL_ANALYSIS = "technical_analysis"
    NEWS_ANALYSIS = "news_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    STRATEGY_RECOMMENDATION = "strategy_recommendation"
    PATTERN_RECOGNITION = "pattern_recognition"
    CORRELATION_ANALYSIS = "correlation_analysis"


class ModelCapability(str, Enum):
    """Capabilities of the Gemma3 model"""
    TEXT_GENERATION = "text_generation"
    INSTRUCTION_FOLLOWING = "instruction_following"
    MARKET_ANALYSIS = "market_analysis"
    RISK_EVALUATION = "risk_evaluation"
    PATTERN_DETECTION = "pattern_detection"
    SENTIMENT_SCORING = "sentiment_scoring"
    PREDICTION_GENERATION = "prediction_generation"


class Gemma3IntegrationError(Exception):
    """Base exception for Gemma3 integration errors"""
    def __init__(self, message: str, error_code: str = None, model_response: str = None):
        self.message = message
        self.error_code = error_code
        self.model_response = model_response
        super().__init__(self.message)


class ModelConnectionError(Gemma3IntegrationError):
    """Exception for model connection issues"""
    pass


class ModelInferenceError(Gemma3IntegrationError):
    """Exception for model inference errors"""
    pass


class ModelValidationError(Gemma3IntegrationError):
    """Exception for input/output validation errors"""
    pass


@dataclass
class AnalysisRequest:
    """Request structure for Gemma3 analysis"""
    analysis_type: AnalysisType
    input_data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    confidence_threshold: float = 0.6
    timeout: int = 60


@dataclass
class AnalysisResponse:
    """Response structure from Gemma3 analysis"""
    analysis_type: AnalysisType
    result: Dict[str, Any]
    confidence_score: float
    processing_time_ms: float
    model_version: str
    token_count: int
    raw_response: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class MarketContext:
    """Market context for AI analysis"""
    symbol: str
    current_price: float
    price_change_pct: float
    volume: int
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    technical_indicators: Dict[str, float] = field(default_factory=dict)
    news_sentiment: Optional[float] = None


class Gemma3Client:
    """
    Ollama Gemma3 integration client for NIRAJ trading system

    This client provides AI-powered analysis capabilities using the Gemma3 model
    through Ollama's API, specialized for trading and financial analysis tasks.
    """

    def __init__(self):
        """Initialize the Gemma3 client with configuration"""
        self.base_url = get_config('ai.ollama.base_url', 'http://localhost:11434')
        self.model_name = get_config('ai.ollama.model', 'gemma3:4b-it-q4_K_M')
        self.timeout = get_config('ai.ollama.timeout', 120)
        self.max_tokens = get_config('ai.ollama.max_tokens', 4096)
        self.temperature = get_config('ai.ollama.temperature', 0.7)

        # Model tracking
        self.ai_model: Optional[AIModel] = None
        self.session = None
        self.is_connected = False
        self.model_capabilities = [
            ModelCapability.TEXT_GENERATION,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.MARKET_ANALYSIS,
            ModelCapability.RISK_EVALUATION,
            ModelCapability.PATTERN_DETECTION,
            ModelCapability.SENTIMENT_SCORING,
            ModelCapability.PREDICTION_GENERATION
        ]

        # Performance tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.average_response_time = 0.0

        logger.info(
            "Gemma3 client initialized",
            base_url=self.base_url,
            model=self.model_name,
            timeout=self.timeout
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self) -> bool:
        """
        Establish connection to Ollama server and initialize model

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create HTTP session
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )

            # Test connection
            await self._test_connection()

            # Initialize AI model tracking
            await self._initialize_model_tracking()

            self.is_connected = True
            logger.info("Successfully connected to Ollama server", model=self.model_name)
            return True

        except Exception as e:
            logger.error("Failed to connect to Ollama server", error=str(e))
            self.is_connected = False
            if self.session:
                await self.session.close()
                self.session = None
            raise ModelConnectionError(f"Failed to connect to Ollama: {str(e)}")

    async def disconnect(self):
        """Disconnect from Ollama server"""
        try:
            if self.session:
                await self.session.close()
                self.session = None

            self.is_connected = False
            logger.info("Disconnected from Ollama server")

        except Exception as e:
            logger.error("Error during disconnection", error=str(e))

    async def _test_connection(self):
        """Test connection to Ollama server"""
        try:
            url = f"{self.base_url}/api/tags"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [model.get('name', '') for model in data.get('models', [])]

                    if not any(self.model_name in model for model in models):
                        logger.warning(
                            "Model not found on server",
                            model=self.model_name,
                            available_models=models
                        )
                        # Try to pull the model
                        await self._pull_model()

                else:
                    raise ModelConnectionError(f"Server responded with status {response.status}")

        except aiohttp.ClientError as e:
            raise ModelConnectionError(f"Connection test failed: {str(e)}")

    async def _pull_model(self):
        """Pull the model if it's not available"""
        try:
            logger.info("Attempting to pull model", model=self.model_name)
            url = f"{self.base_url}/api/pull"
            payload = {"name": self.model_name}

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info("Model pull initiated", model=self.model_name)
                else:
                    logger.error("Failed to pull model", status=response.status)

        except Exception as e:
            logger.error("Error pulling model", error=str(e))

    async def _initialize_model_tracking(self):
        """Initialize AI model tracking in database"""
        try:
            self.ai_model = AIModel(
                name="Ollama-Gemma3-NIRAJ",
                description="Gemma3 model via Ollama for NIRAJ trading analysis",
                model_type=ModelType.TRANSFORMER,
                version=self.model_name.split(':')[-1] if ':' in self.model_name else "latest",
                learning_mode=LearningMode.SUPERVISED,
                status=ModelStatus.DEPLOYED,
                is_production_ready=True,
                hyperparameters={
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "model_name": self.model_name
                },
                architecture_config={
                    "base_url": self.base_url,
                    "timeout": self.timeout,
                    "capabilities": [cap.value for cap in self.model_capabilities]
                },
                tags=["ollama", "gemma3", "trading", "nlp"],
                metadata={
                    "provider": "Ollama",
                    "model_family": "Gemma",
                    "use_case": "Trading Analysis",
                    "initialized_at": datetime.utcnow().isoformat()
                }
            )

            logger.info("AI model tracking initialized", model_id=self.ai_model.model_id)

        except Exception as e:
            logger.error("Failed to initialize model tracking", error=str(e))

    async def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Perform AI analysis using Gemma3 model

        Args:
            request: Analysis request with input data and parameters

        Returns:
            Analysis response with results and metadata

        Raises:
            ModelInferenceError: If analysis fails
        """
        if not self.is_connected:
            await self.connect()

        start_time = time.time()
        self.total_requests += 1

        try:
            # Validate request
            self._validate_analysis_request(request)

            # Build prompt based on analysis type
            prompt = self._build_prompt(request)

            # Make API call to Ollama
            raw_response = await self._make_api_call(prompt, request.max_tokens, request.temperature)

            # Parse and structure response
            result = self._parse_response(raw_response, request.analysis_type)

            # Calculate confidence score
            confidence_score = self._calculate_confidence(result, request.confidence_threshold)

            processing_time = (time.time() - start_time) * 1000

            # Update performance metrics
            self.successful_requests += 1
            self._update_performance_metrics(processing_time)

            # Record prediction if applicable
            if self.ai_model and request.analysis_type in [
                AnalysisType.PRICE_PREDICTION,
                AnalysisType.STRATEGY_RECOMMENDATION
            ]:
                await self._record_prediction(request, result, confidence_score)

            response = AnalysisResponse(
                analysis_type=request.analysis_type,
                result=result,
                confidence_score=confidence_score,
                processing_time_ms=processing_time,
                model_version=self.model_name,
                token_count=len(raw_response.split()),
                raw_response=raw_response,
                metadata={
                    "request_id": f"req_{int(time.time())}_{self.total_requests}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "input_hash": self._hash_input(request.input_data)
                }
            )

            logger.info(
                "Analysis completed successfully",
                analysis_type=request.analysis_type.value,
                confidence=confidence_score,
                processing_time_ms=processing_time
            )

            return response

        except Exception as e:
            self.failed_requests += 1
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(
                "Analysis failed",
                analysis_type=request.analysis_type.value,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )

            return AnalysisResponse(
                analysis_type=request.analysis_type,
                result={},
                confidence_score=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
                model_version=self.model_name,
                token_count=0,
                raw_response="",
                error=error_msg
            )

    def _validate_analysis_request(self, request: AnalysisRequest):
        """Validate analysis request parameters"""
        if not request.input_data:
            raise ModelValidationError("Input data cannot be empty")

        if request.max_tokens <= 0 or request.max_tokens > 8192:
            raise ModelValidationError("max_tokens must be between 1 and 8192")

        if not (0.0 <= request.temperature <= 2.0):
            raise ModelValidationError("temperature must be between 0.0 and 2.0")

        if not (0.0 <= request.confidence_threshold <= 1.0):
            raise ModelValidationError("confidence_threshold must be between 0.0 and 1.0")

    def _build_prompt(self, request: AnalysisRequest) -> str:
        """Build specialized prompt based on analysis type"""
        base_prompt = "You are NIRAJ, an advanced AI trading assistant. "

        if request.analysis_type == AnalysisType.MARKET_SENTIMENT:
            prompt = base_prompt + self._build_sentiment_prompt(request.input_data)
        elif request.analysis_type == AnalysisType.PRICE_PREDICTION:
            prompt = base_prompt + self._build_price_prediction_prompt(request.input_data)
        elif request.analysis_type == AnalysisType.TECHNICAL_ANALYSIS:
            prompt = base_prompt + self._build_technical_analysis_prompt(request.input_data)
        elif request.analysis_type == AnalysisType.NEWS_ANALYSIS:
            prompt = base_prompt + self._build_news_analysis_prompt(request.input_data)
        elif request.analysis_type == AnalysisType.RISK_ASSESSMENT:
            prompt = base_prompt + self._build_risk_assessment_prompt(request.input_data)
        elif request.analysis_type == AnalysisType.STRATEGY_RECOMMENDATION:
            prompt = base_prompt + self._build_strategy_recommendation_prompt(request.input_data)
        elif request.analysis_type == AnalysisType.PATTERN_RECOGNITION:
            prompt = base_prompt + self._build_pattern_recognition_prompt(request.input_data)
        elif request.analysis_type == AnalysisType.CORRELATION_ANALYSIS:
            prompt = base_prompt + self._build_correlation_analysis_prompt(request.input_data)
        else:
            prompt = base_prompt + f"Analyze the following data: {json.dumps(request.input_data)}"

        # Add context if provided
        if request.context:
            prompt += f"\n\nContext: {json.dumps(request.context)}"

        # Add output format instructions
        prompt += "\n\nProvide your response in JSON format with the following structure:"
        prompt += "\n{"
        prompt += '\n  "analysis": "your detailed analysis",  '
        prompt += '\n  "confidence": 0.85,  '
        prompt += '\n  "recommendation": "your recommendation",  '
        prompt += '\n  "key_points": ["point1", "point2", ...],  '
        prompt += '\n  "risk_level": "low|medium|high",  '
        prompt += '\n  "rationale": "explanation of your reasoning"'
        prompt += "\n}"

        return prompt

    def _build_sentiment_prompt(self, data: Dict[str, Any]) -> str:
        """Build prompt for market sentiment analysis"""
        return f"""
        Analyze the market sentiment from the following data:
        {json.dumps(data, indent=2)}

        Consider factors like:
        - News headlines and content
        - Social media sentiment
        - Market indicators
        - Trading volume patterns

        Provide sentiment score (-1 to 1), key sentiment drivers, and market implications.
        """

    def _build_price_prediction_prompt(self, data: Dict[str, Any]) -> str:
        """Build prompt for price prediction analysis"""
        return f"""
        Predict price movement based on the following market data:
        {json.dumps(data, indent=2)}

        Consider:
        - Historical price patterns
        - Technical indicators
        - Volume analysis
        - Market trends
        - Support and resistance levels

        Provide direction (up/down/sideways), target price range, time horizon, and confidence level.
        """

    def _build_technical_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Build prompt for technical analysis"""
        return f"""
        Perform technical analysis on the following data:
        {json.dumps(data, indent=2)}

        Analyze:
        - Chart patterns
        - Technical indicators (RSI, MACD, Moving averages)
        - Support and resistance levels
        - Volume patterns
        - Trend analysis

        Provide clear buy/sell/hold signals with reasoning.
        """

    def _build_news_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Build prompt for news analysis"""
        return f"""
        Analyze the impact of news on market movements:
        {json.dumps(data, indent=2)}

        Evaluate:
        - News sentiment and tone
        - Potential market impact
        - Relevance to specific stocks/sectors
        - Short-term vs long-term implications

        Provide sentiment score, impact assessment, and trading implications.
        """

    def _build_risk_assessment_prompt(self, data: Dict[str, Any]) -> str:
        """Build prompt for risk assessment"""
        return f"""
        Assess the risk profile of the following position/strategy:
        {json.dumps(data, indent=2)}

        Evaluate:
        - Market risk factors
        - Volatility levels
        - Position sizing appropriateness
        - Correlation risks
        - Liquidity concerns

        Provide risk rating, key risk factors, and mitigation suggestions.
        """

    def _build_strategy_recommendation_prompt(self, data: Dict[str, Any]) -> str:
        """Build prompt for strategy recommendation"""
        return f"""
        Recommend trading strategies based on current market conditions:
        {json.dumps(data, indent=2)}

        Consider:
        - Market regime (bull/bear/sideways)
        - Volatility environment
        - Available instruments
        - Risk tolerance
        - Time horizon

        Recommend specific strategies with entry/exit criteria and risk management.
        """

    def _build_pattern_recognition_prompt(self, data: Dict[str, Any]) -> str:
        """Build prompt for pattern recognition"""
        return f"""
        Identify patterns in the following market data:
        {json.dumps(data, indent=2)}

        Look for:
        - Chart patterns (triangles, flags, head & shoulders)
        - Candlestick patterns
        - Volume patterns
        - Breakout/breakdown patterns
        - Seasonal patterns

        Describe identified patterns and their trading implications.
        """

    def _build_correlation_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Build prompt for correlation analysis"""
        return f"""
        Analyze correlations in the following data:
        {json.dumps(data, indent=2)}

        Examine:
        - Asset correlations
        - Sector correlations
        - Market factor correlations
        - Temporal correlation changes

        Provide correlation insights and portfolio diversification recommendations.
        """

    async def _make_api_call(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Make API call to Ollama"""
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('response', '')
                else:
                    error_text = await response.text()
                    raise ModelInferenceError(
                        f"API call failed with status {response.status}: {error_text}"
                    )

        except aiohttp.ClientError as e:
            raise ModelInferenceError(f"HTTP request failed: {str(e)}")

    def _parse_response(self, raw_response: str, analysis_type: AnalysisType) -> Dict[str, Any]:
        """Parse and structure the model response"""
        try:
            # Try to extract JSON from the response
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = raw_response[json_start:json_end]
                result = json.loads(json_str)
            else:
                # Fallback: structure unstructured response
                result = {
                    "analysis": raw_response,
                    "confidence": 0.5,
                    "recommendation": "Manual review required",
                    "key_points": ["Unstructured response received"],
                    "risk_level": "medium",
                    "rationale": "Response parsing required manual interpretation"
                }

            # Ensure required fields exist
            required_fields = ["analysis", "confidence", "recommendation", "key_points", "risk_level"]
            for field in required_fields:
                if field not in result:
                    result[field] = "Not provided"

            # Validate confidence score
            if isinstance(result.get("confidence"), (int, float)):
                result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
            else:
                result["confidence"] = 0.5

            return result

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response", raw_response=raw_response[:200])
            return {
                "analysis": raw_response,
                "confidence": 0.3,
                "recommendation": "Manual review required",
                "key_points": ["JSON parsing failed"],
                "risk_level": "medium",
                "rationale": "Response format not as expected"
            }

    def _calculate_confidence(self, result: Dict[str, Any], threshold: float) -> float:
        """Calculate overall confidence score"""
        try:
            model_confidence = float(result.get("confidence", 0.5))

            # Adjust confidence based on response quality
            quality_factors = []

            # Check if analysis is detailed
            analysis_text = result.get("analysis", "")
            if len(analysis_text) > 100:
                quality_factors.append(0.1)

            # Check if key points are provided
            key_points = result.get("key_points", [])
            if isinstance(key_points, list) and len(key_points) >= 3:
                quality_factors.append(0.1)

            # Check if recommendation is specific
            recommendation = result.get("recommendation", "")
            if len(recommendation) > 20 and "review" not in recommendation.lower():
                quality_factors.append(0.1)

            # Calculate final confidence
            quality_bonus = sum(quality_factors)
            final_confidence = min(1.0, model_confidence + quality_bonus)

            return final_confidence

        except Exception:
            return 0.5

    def _hash_input(self, input_data: Dict[str, Any]) -> str:
        """Generate hash of input data for tracking"""
        import hashlib
        input_str = json.dumps(input_data, sort_keys=True)
        return hashlib.sha256(input_str.encode()).hexdigest()[:16]

    def _update_performance_metrics(self, processing_time: float):
        """Update performance tracking metrics"""
        if self.total_requests == 1:
            self.average_response_time = processing_time
        else:
            self.average_response_time = (
                (self.average_response_time * (self.total_requests - 1) + processing_time)
                / self.total_requests
            )

        # Update AI model metrics if available
        if self.ai_model:
            self.ai_model.record_prediction(
                success=True,
                inference_time_ms=processing_time
            )

    async def _record_prediction(self, request: AnalysisRequest, result: Dict[str, Any], confidence: float):
        """Record prediction for tracking and validation"""
        try:
            if not self.ai_model:
                return

            # Determine prediction type
            prediction_type = PredictionType.PRICE_DIRECTION
            if request.analysis_type == AnalysisType.PRICE_PREDICTION:
                prediction_type = PredictionType.PRICE_TARGET
            elif request.analysis_type == AnalysisType.STRATEGY_RECOMMENDATION:
                prediction_type = PredictionType.BUY_SIGNAL

            # Create prediction record
            prediction = AIPrediction(
                model_id=self.ai_model.model_id,
                prediction_type=prediction_type,
                prediction_value=result,
                confidence_score=confidence,
                input_features=request.input_data,
                market_context=request.context or {},
                expiry_time=datetime.utcnow() + timedelta(hours=24),
                algorithm_parameters={
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "analysis_type": request.analysis_type.value
                },
                tags=["gemma3", "ollama", request.analysis_type.value],
                metadata={
                    "model_version": self.model_name,
                    "request_timestamp": datetime.utcnow().isoformat()
                }
            )

            # Calculate input hash
            prediction.calculate_input_hash()

            logger.info(
                "Prediction recorded",
                prediction_id=prediction.prediction_id,
                type=prediction_type.value,
                confidence=confidence
            )

        except Exception as e:
            logger.error("Failed to record prediction", error=str(e))

    async def analyze_market_sentiment(self, market_data: Dict[str, Any], news_data: List[Dict[str, Any]] = None) -> AnalysisResponse:
        """Analyze overall market sentiment"""
        input_data = {
            "market_data": market_data,
            "news_data": news_data or []
        }

        request = AnalysisRequest(
            analysis_type=AnalysisType.MARKET_SENTIMENT,
            input_data=input_data,
            confidence_threshold=0.7
        )

        return await self.analyze(request)

    async def predict_price_movement(self, symbol: str, market_context: MarketContext, timeframe: str = "1d") -> AnalysisResponse:
        """Predict price movement for a specific symbol"""
        input_data = {
            "symbol": symbol,
            "current_price": market_context.current_price,
            "price_change_pct": market_context.price_change_pct,
            "volume": market_context.volume,
            "technical_indicators": market_context.technical_indicators,
            "timeframe": timeframe,
            "sector": market_context.sector,
            "market_cap": market_context.market_cap
        }

        context = {
            "timestamp": market_context.timestamp.isoformat(),
            "news_sentiment": market_context.news_sentiment
        }

        request = AnalysisRequest(
            analysis_type=AnalysisType.PRICE_PREDICTION,
            input_data=input_data,
            context=context,
            confidence_threshold=0.8
        )

        return await self.analyze(request)

    async def analyze_technical_indicators(self, symbol: str, indicators: Dict[str, float], chart_data: List[Dict[str, Any]]) -> AnalysisResponse:
        """Analyze technical indicators and chart patterns"""
        input_data = {
            "symbol": symbol,
            "indicators": indicators,
            "chart_data": chart_data[-100:],  # Last 100 data points
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

        request = AnalysisRequest(
            analysis_type=AnalysisType.TECHNICAL_ANALYSIS,
            input_data=input_data,
            confidence_threshold=0.75
        )

        return await self.analyze(request)

    async def assess_portfolio_risk(self, portfolio_data: Dict[str, Any], market_conditions: Dict[str, Any]) -> AnalysisResponse:
        """Assess portfolio risk and provide recommendations"""
        input_data = {
            "portfolio": portfolio_data,
            "market_conditions": market_conditions,
            "assessment_time": datetime.utcnow().isoformat()
        }

        request = AnalysisRequest(
            analysis_type=AnalysisType.RISK_ASSESSMENT,
            input_data=input_data,
            confidence_threshold=0.8
        )

        return await self.analyze(request)

    async def recommend_strategies(self, market_regime: str, risk_tolerance: str, available_capital: float) -> AnalysisResponse:
        """Recommend trading strategies based on current conditions"""
        input_data = {
            "market_regime": market_regime,
            "risk_tolerance": risk_tolerance,
            "available_capital": available_capital,
            "recommendation_time": datetime.utcnow().isoformat()
        }

        request = AnalysisRequest(
            analysis_type=AnalysisType.STRATEGY_RECOMMENDATION,
            input_data=input_data,
            confidence_threshold=0.75
        )

        return await self.analyze(request)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        success_rate = (self.successful_requests / self.total_requests) if self.total_requests > 0 else 0.0

        metrics = {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "average_response_time_ms": self.average_response_time,
            "is_connected": self.is_connected,
            "model_name": self.model_name,
            "capabilities": [cap.value for cap in self.model_capabilities]
        }

        if self.ai_model:
            metrics["model_id"] = self.ai_model.model_id
            metrics["model_performance"] = self.ai_model.get_performance_summary()

        return metrics

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the Gemma3 integration"""
        try:
            if not self.is_connected:
                await self.connect()

            # Test with a simple query
            test_request = AnalysisRequest(
                analysis_type=AnalysisType.MARKET_SENTIMENT,
                input_data={"test": "health_check"},
                max_tokens=50,
                temperature=0.1,
                timeout=10
            )

            start_time = time.time()
            response = await self.analyze(test_request)
            response_time = (time.time() - start_time) * 1000

            return {
                "status": "healthy" if not response.error else "degraded",
                "connected": self.is_connected,
                "model": self.model_name,
                "response_time_ms": response_time,
                "error": response.error,
                "performance": self.get_performance_metrics()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "model": self.model_name
            }


# Global client instance
gemma3_client = Gemma3Client()


# Convenience functions
async def get_market_sentiment(market_data: Dict[str, Any], news_data: List[Dict[str, Any]] = None) -> AnalysisResponse:
    """Get market sentiment analysis"""
    async with gemma3_client:
        return await gemma3_client.analyze_market_sentiment(market_data, news_data)


async def predict_price(symbol: str, market_context: MarketContext, timeframe: str = "1d") -> AnalysisResponse:
    """Get price prediction"""
    async with gemma3_client:
        return await gemma3_client.predict_price_movement(symbol, market_context, timeframe)


async def get_strategy_recommendation(market_regime: str, risk_tolerance: str, capital: float) -> AnalysisResponse:
    """Get strategy recommendation"""
    async with gemma3_client:
        return await gemma3_client.recommend_strategies(market_regime, risk_tolerance, capital)


async def check_ai_health() -> Dict[str, Any]:
    """Check AI system health"""
    return await gemma3_client.health_check()


# Example usage and testing functions
async def example_usage():
    """Example usage of the Gemma3 integration"""

    # Example market context
    market_context = MarketContext(
        symbol="BANKNIFTY",
        current_price=45250.0,
        price_change_pct=1.2,
        volume=1500000,
        sector="Banking",
        technical_indicators={
            "rsi": 68.5,
            "macd": 0.15,
            "sma_20": 44800.0,
            "sma_50": 44200.0
        },
        news_sentiment=0.3
    )

    async with gemma3_client:
        # Price prediction
        price_prediction = await gemma3_client.predict_price_movement(
            symbol="BANKNIFTY",
            market_context=market_context,
            timeframe="1h"
        )

        print("Price Prediction:", price_prediction.result)

        # Strategy recommendation
        strategy_rec = await gemma3_client.recommend_strategies(
            market_regime="bullish",
            risk_tolerance="medium",
            available_capital=100000.0
        )

        print("Strategy Recommendation:", strategy_rec.result)

        # Performance metrics
        metrics = gemma3_client.get_performance_metrics()
        print("Performance Metrics:", metrics)


if __name__ == "__main__":
    # Run example usage
    asyncio.run(example_usage())
