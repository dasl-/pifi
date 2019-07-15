import React from 'react';

class Default extends React.Component {
  render() {
    return (
      <div className="col-xs-12">
        <strong>You need to create .env files then rebuild!</strong><br/>
        /home/pi/lightness/app/.env.development<br/>
        /home/pi/lightness/app/.env.production<br/><br/>

        Contents:<br/>
        <pre>
REACT_APP_GOOGLE_API_KEY=YOUR_KEY_HERE<br/>
REACT_APP_GOOGLE_API_CLIENT_ID=YOUR_CLIENT_ID_HERE<br/>
REACT_APP_API_BASE_URL=http://YOUR_URL/api
        </pre>
      </div>
    );
  }
}

export default Default;