# ORCOV19-webservice
ORCOV19-webservice is the backend to the ORCOV19 dashboard, which shows the current status of Oregon's hospital capacity and 
PPE supply shipments in response to COVID-19. (https://orcov19.live)

![ORCOV19](https://raw.githubusercontent.com/ChangYuJonathanWu/orcov19/master/public/orcov19.jpg)

The backend aggressively caches "good data" in-memory due to data sources being unstructured, regularly
changing and being unavailable. 

Many endpoints and backend functionality are no longer in use but have been left in place to show the different approaches
taken to adapt to highly-variable data sources and frequent data availability issues.

## Built With:

- [Flask](https://flask.palletsprojects.com/en/1.1.x/)
    * Webservice, routing, caching and (now deprecated) administrative interface.
- [Beautiful Soup 4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
    * Scraping Oregon hospital supply and capacity data.
- [SQLAlchemy](https://www.sqlalchemy.org/)
    * Used to cache and manually set data in PostgreSQL database (functionality now deprecated).
    
## Usage:
1. Install dependencies:
```
pip install -r requirements.txt
```
2. Start the webservice:
```
flask run
```
