import React from 'react';

class InvalidBuild extends React.Component {
  render() {
    return (
      <div className="col-xs-12">
        <strong>You need to create .env files then rebuild!</strong><br/>
        <pre className="text-light">
          &lt;path to repo&gt;/app/.env.development<br/>
          &lt;path to repo&gt;/app/.env.production<br/><br/>
        </pre>

        Contents:<br/>
        <pre className="text-light">
          REACT_APP_GOOGLE_API_KEY=YOUR_KEY_HERE<br/>
          REACT_APP_GOOGLE_API_CLIENT_ID=YOUR_CLIENT_ID_HERE<br/>
        </pre>
      </div>
    );
  }
}

export default InvalidBuild;
