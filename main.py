from json import JSONDecodeError
from typing import Dict, List, Optional, Union, Any

from fastapi import FastAPI, Request, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field,RootModel
from starlette.middleware.base import BaseHTTPMiddleware
from token_bucket import TokenBucket
try:
    from nepse import Nepse
except ImportError:
    import sys
    sys.path.append("../")
    from nepse import Nepse

# Define models for documentation
class NepseIndexModel(BaseModel):
    index: str
    currentValue: float = Field(..., description="Current value of the index")
    previousValue: float = Field(..., description="Previous value of the index")
    pointChange: float = Field(..., description="Point change in the index")
    percentageChange: float = Field(..., description="Percentage change in the index")

class CompanyModel(BaseModel):
    symbol: str = Field(..., description="Company symbol/ticker")
    securityName: str = Field(..., description="Name of the security")
    securityId: int = Field(..., description="Security ID")
    sectorName: str = Field(..., description="Sector the company belongs to")
    instrumentType: str = Field(..., description="Type of instrument")
    totalQuantity: Optional[int] = Field(None, description="Total quantity of shares")
    
class ScripPriceModel(BaseModel):
    date: str = Field(..., description="Date of the price data")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")

class SummaryResponse(BaseModel):
   RootModel: Dict[str, Any] = Field(..., description="Summary of market data")

# Create FastAPI app
app = FastAPI(
    title="Nepal Stock Exchange API",
    description="""
    API for Nepal Stock Exchange (NEPSE) market data. 
    
    This API provides access to real-time and historical data from the Nepal Stock Exchange,
    including indices, stock prices, company information, and market statistics.
    
    All endpoints return JSON responses unless otherwise specified.
    """,
    version="1.0.0",
    contact={
        "name": "NEPSE API",
        "url": "https://www.nepalstock.com/",
    },
    license_info={
        "name": "MIT License",
    },
    openapi_tags=[
        {
            "name": "Market Indices",
            "description": "Endpoints related to market indices and sub-indices",
        },
        {
            "name": "Company Data",
            "description": "Endpoints for company and security information",
        },
        {
            "name": "Market Statistics",
            "description": "Endpoints for various market statistics and rankings",
        },
        {
            "name": "Price Data",
            "description": "Endpoints for price and volume data",
        },
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, bucket: TokenBucket):
        super().__init__(app)
        self.bucket = bucket  # Initialize the middleware with a token bucket

    async def dispatch(self, request: Request, call_next):
        # Process each incoming request
        if self.bucket.take_token():
            # If a token is available, proceed with the request
            return await call_next(request)
        # If no tokens are available, return a 429 error (rate limit exceeded)
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

# Initialize the token bucket with 4 tokens capacity and refill rate of 2 tokens/second
bucket = TokenBucket(capacity=4, refill_rate=2)

# Add the rate limiting middleware to the FastAPI app
app.add_middleware(RateLimiterMiddleware, bucket=bucket)


nepse = Nepse()
nepse.setTLSVerification(False)

routes = {
    "PriceVolume": "/price-volume",
    "Summary": "/summary",
    "SupplyDemand": "/supply-demand",
    "TopGainers": "/top-gainers",
    "TopLosers": "/top-losers",
    "TopTenTradeScrips": "/top-ten-trade-scrips",
    "TopTenTurnoverScrips": "/top-ten-turnover-scrips",
    "TopTenTransactionScrips": "/top-ten-transaction-scrips",
    "IsNepseOpen": "/is-nepse-open",
    "NepseIndex": "/nepse-index",
    "NepseSubIndices": "/nepse-sub-indices",
    "DailyNepseIndexGraph": "/daily-Nep-graph",
    "DailyScripPriceGraph": "/daily-scrip-price-graph",
    "CompanyList": "/company-list",
    "SecurityList": "/security-list",
    "TradeTurnoverTransactionSubindices": "/trade-turnover-transaction-subindices",
    "LiveMarket": "/live-market",
    "MarketDepth": "/market-depth",
}


@app.get("/")
def get_root():
    return {
        "message": "Welcome to the Nepal Stock Exchange API",
        "description": "This API provides access to NEPSE market data.",
        "available_routes": routes,
        "documentation": {
            "openapi": "/openapi.json",
            "swagger": "/docs",
        }
    }


@app.get(
    routes["Summary"],
    response_model=SummaryResponse,
    tags=["Market Statistics"],
    summary="Get market summary",
    description="Returns the summary of today's market activity including turnover, volume, and other key metrics"
)
def get_summary():
    return JSONResponse(content=_getSummary())


def _getSummary():
    response = dict()
    for obj in nepse.getSummary():
        response[obj["detail"]] = obj["value"]
    return response


@app.get(
    routes["NepseIndex"],
    tags=["Market Indices"],
    summary="Get Nepse Index",
    description="Returns the current NEPSE index value along with change information"
)
def get_nepse_index():
    return _get_nepse_index()


def _get_nepse_index():
    response = dict()
    for obj in nepse.getNepseIndex():
        response[obj["index"]] = obj
    return response


@app.get(
    routes["NepseSubIndices"],
    tags=["Market Indices"],
    summary="Get Nepse Sub-Indices",
    description="Returns all sub-indices of NEPSE including banking, development banks, hydropower, etc."
)
def get_nepse_sub_indices():
    return _get_nepse_sub_indices()


def _get_nepse_sub_indices():
    response = dict()
    for obj in nepse.getNepseSubIndices():
        response[obj["index"]] = obj
    return response


@app.get(
    routes["TopTenTradeScrips"],
    tags=["Market Statistics"],
    summary="Get top ten trade scrips",
    description="Returns the top ten scrips by trade volume"
)
def get_top_ten_trade_scrips():
    return nepse.getTopTenTradeScrips()


@app.get(
    routes["TopTenTransactionScrips"],
    tags=["Market Statistics"],
    summary="Get top ten transaction scrips",
    description="Returns the top ten scrips by number of transactions"
)
def get_top_ten_transaction_scrips():
    return nepse.getTopTenTransactionScrips()


@app.get(
    routes["TopTenTurnoverScrips"],
    tags=["Market Statistics"],
    summary="Get top ten turnover scrips",
    description="Returns the top ten scrips by turnover value"
)
def get_top_ten_turnover_scrips():
    return nepse.getTopTenTurnoverScrips()


@app.get(
    routes["SupplyDemand"],
    tags=["Market Statistics"],
    summary="Get supply and demand data",
    description="Returns the supply and demand statistics for the market"
)
def get_supply_demand():
    return nepse.getSupplyDemand()


@app.get(
    routes["TopGainers"],
    tags=["Market Statistics"],
    summary="Get top gainers",
    description="Returns the list of stocks with highest positive price change"
)
def get_top_gainers():
    return nepse.getTopGainers()


@app.get(
    routes["TopLosers"],
    tags=["Market Statistics"],
    summary="Get top losers",
    description="Returns the list of stocks with highest negative price change"
)
def get_top_losers():
    return nepse.getTopLosers()


@app.get(
    routes["IsNepseOpen"],
    tags=["Market Statistics"],
    summary="Check if NEPSE is open",
    description="Returns whether the Nepal Stock Exchange is currently open for trading"
)
def is_nepse_open():
    return nepse.isNepseOpen()


@app.get(
    routes["DailyNepseIndexGraph"],
    tags=["Market Indices"],
    summary="Get daily NEPSE index graph data",
    description="Returns historical data for the NEPSE index that can be used to generate graphs"
)
def get_daily_nepse_index_graph():
    return nepse.getDailyNepseIndexGraph()


@app.get(
    f"{routes['DailyScripPriceGraph']}",
    response_class=HTMLResponse,
    tags=["Price Data"],
    summary="List all available scrips"
)
def list_daily_scrip_price_graph():
    symbols = nepse.getSecurityList()
    response = "<BR>".join(
        [
            f"<a href={routes['DailyScripPriceGraph']}/{symbol['symbol']}> {symbol['symbol']} </a>"
            for symbol in symbols
        ]
    )
    return HTMLResponse(content=f"<h1>Available Scrips</h1>{response}")

@app.get(
    f"{routes['DailyScripPriceGraph']}/{{symbol}}",
    tags=["Price Data"],
    summary="Get daily price graph for a specific scrip",
    description="Returns the historical price data for the specified stock symbol",
    response_model=List[Dict[str, Any]]
)
def get_daily_scrip_price_graph(
    symbol: str = Path(..., description="Stock symbol/ticker to fetch data for")
):
    try:
        return nepse.getDailyScripPriceGraph(symbol)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Data for symbol {symbol} not found: {str(e)}")


@app.get(
    routes["CompanyList"],
    tags=["Company Data"],
    summary="Get company list",
    description="Returns the list of all companies listed on NEPSE"
)
def get_company_list():
    return nepse.getCompanyList()


@app.get(
    routes["SecurityList"],
    tags=["Company Data"],
    summary="Get security list",
    description="Returns the list of all securities available on NEPSE"
)
def get_security_list():
    return nepse.getSecurityList()


@app.get(
    routes["PriceVolume"],
    tags=["Price Data"],
    summary="Get price and volume data",
    description="Returns price and volume data for all securities"
)
def get_price_volume():
    return nepse.getPriceVolume()


@app.get(
    routes["LiveMarket"],
    tags=["Market Statistics"],
    summary="Get live market data",
    description="Returns real-time market data for all securities currently trading"
)
def get_live_market():
    return nepse.getLiveMarket()


@app.get(
    f"{routes['MarketDepth']}",
    response_class=HTMLResponse,
    tags=["Market Statistics"],
    summary="List all symbols for market depth"
)
def list_market_depth():
    symbols = nepse.getSecurityList()
    response = "<BR>".join(
        [
            f"<a href={routes['MarketDepth']}/{symbol['symbol']}> {symbol['symbol']} </a>"
            for symbol in symbols
        ]
    )
    return HTMLResponse(content=f"<h1>Market Depth - Available Symbols</h1>{response}")

@app.get(
    f"{routes['MarketDepth']}/{{symbol}}",
    tags=["Market Statistics"],
    summary="Get market depth for a specific symbol",
    description="Returns buy/sell orders in the order book for the specified symbol"
)
def get_market_depth(
    symbol: str = Path(..., description="Stock symbol/ticker to fetch market depth for")
):
    try:
        data = nepse.getSymbolMarketDepth(symbol)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Market depth for {symbol} not available")
        return data
    except JSONDecodeError:
        raise HTTPException(status_code=404, detail=f"Invalid data received for {symbol}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching market depth: {str(e)}")


@app.get(
    routes["TradeTurnoverTransactionSubindices"],
    tags=["Market Statistics"],
    summary="Get comprehensive market statistics",
    description="""
    Returns detailed statistics for all sectors and securities, including:
    - Trade volume by security and sector
    - Turnover by security and sector
    - Transaction counts by security and sector
    - Sub-index performance
    """
)
def get_trade_turnover_transaction_subindices():
    companies = {company["symbol"]: company for company in nepse.getCompanyList()}
    turnover = {obj["symbol"]: obj for obj in nepse.getTopTenTurnoverScrips()}
    transaction = {obj["symbol"]: obj for obj in nepse.getTopTenTransactionScrips()}
    trade = {obj["symbol"]: obj for obj in nepse.getTopTenTradeScrips()}

    gainers = {obj["symbol"]: obj for obj in nepse.getTopGainers()}
    losers = {obj["symbol"]: obj for obj in nepse.getTopLosers()}

    price_vol_info = {obj["symbol"]: obj for obj in nepse.getPriceVolume()}

    sector_sub_indices = _get_nepse_sub_indices()
    # this is done since nepse sub indices and sector name are different
    sector_mapper = {
        "Commercial Banks": "Banking SubIndex",
        "Development Banks": "Development Bank Index",
        "Finance": "Finance Index",
        "Hotels And Tourism": "Hotels And Tourism Index",
        "Hydro Power": "HydroPower Index",
        "Investment": "Investment Index",
        "Life Insurance": "Life Insurance",
        "Manufacturing And Processing": "Manufacturing And Processing",
        "Microfinance": "Microfinance Index",
        "Mutual Fund": "Mutual Fund",
        "Non Life Insurance": "Non Life Insurance",
        "Others": "Others Index",
        "Tradings": "Trading Index",
    }

    scrips_details = dict()
    for symbol, company in companies.items():
        company_details = {}

        company_details["symbol"] = symbol
        company_details["sectorName"] = company["sectorName"]
        company_details["totalTurnover"] = (
            turnover[symbol]["turnover"] if symbol in turnover.keys() else 0
        )
        company_details["totalTrades"] = (
            transaction[symbol]["totalTrades"] if symbol in transaction.keys() else 0
        )
        company_details["totalTradeQuantity"] = (
            trade[symbol]["shareTraded"] if symbol in transaction.keys() else 0
        )

        if symbol in gainers.keys():
            (
                company_details["pointChange"],
                company_details["percentageChange"],
                company_details["ltp"],
            ) = (
                gainers[symbol]["pointChange"],
                gainers[symbol]["percentageChange"],
                gainers[symbol]["ltp"],
            )
        elif symbol in losers.keys():
            (
                company_details["pointChange"],
                company_details["percentageChange"],
                company_details["ltp"],
            ) = (
                losers[symbol]["pointChange"],
                losers[symbol]["percentageChange"],
                losers[symbol]["ltp"],
            )
        else:
            (
                company_details["pointChange"],
                company_details["percentageChange"],
                company_details["ltp"],
            ) = (0, 0, 0)

        scrips_details[symbol] = company_details

    sector_details = dict()
    sectors = {company["sectorName"] for company in companies.values()}
    for sector in sectors:
        total_trades, total_trade_quantity, total_turnover = 0, 0, 0
        for scrip_details in scrips_details.values():
            if scrip_details["sectorName"] == sector:
                total_trades += scrip_details["totalTrades"]
                total_trade_quantity += scrip_details["totalTradeQuantity"]
                total_turnover += scrip_details["totalTurnover"]

        sector_details[sector] = {
            "totalTrades": total_trades,
            "totalTradeQuantity": total_trade_quantity,
            "totalTurnover": total_turnover,
            "index": sector_sub_indices[sector_mapper[sector]],
            "sectorName": sector,
        }

    return {"scripsDetails": scrips_details, "sectorsDetails": sector_details}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)