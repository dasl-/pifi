import React from 'react';

class InvalidBuild extends React.Component {
  render() {
    return (
      <div className="col-xs-12">
        <strong>You need to create .env files and then rebuild!</strong><br/>
        <pre className="text-light">
          &lt;path to repo&gt;/app/.env.development<br/>
          &lt;path to repo&gt;/app/.env.production<br/><br/>
        </pre>

        Contents:<br/>
        <pre className="text-light">
          REACT_APP_GOOGLE_API_KEY=YOUR_KEY_HERE<br/>
        </pre>

        <p>
          We make use of the <a href='https://developers.google.com/youtube/v3/getting-started'>Youtube Data API v3</a>.
          Steps to get credentials: <a href='https://www.slickremix.com/docs/get-api-key-for-youtube/'>https://www.slickremix.com/docs/get-api-key-for-youtube/</a>.
        </p>
      </div>
    );
  }
}

export default InvalidBuild;
