using System;
using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

bool TESTING = true;

public class CPHInline
{
    private static readonly HttpClient client = new HttpClient();
    private static JObject gunConfig;
    private const string WORDPRESS_API_URL = "http://your-wordpress-site.com/wp-json/nerfbot/v1";

    public bool Execute()
    {
        // Ensure the gun configuration is loaded
        if (gunConfig == null)
        {
            LoadGunConfig().Wait();
        }

        string username = args["user"].ToString();
        string message = args["message"].ToString();

        // Check if the message is a valid !fire command
        if (!message.StartsWith("!fire"))
        {
            return false;
        }

        string[] parts = message.Split(' ');
        if (parts.Length != 4)
        {
            CPH.SendMessage("Invalid fire command. Usage: !fire x y z");
            return false;
        }

        // Parse command parameters
        if (!int.TryParse(parts[1], out int x) || 
            !int.TryParse(parts[2], out int y) || 
            !int.TryParse(parts[3], out int z))
        {
            CPH.SendMessage("Invalid fire command parameters. x, y, and z must be integers.");
            return false;
        }

         // Check angle limits
        int minHorizontal = (int)gunConfig["min_horizontal"];
        int maxHorizontal = (int)gunConfig["max_horizontal"];
        int minVertical = (int)gunConfig["min_vertical"];
        int maxVertical = (int)gunConfig["max_vertical"];

        if (x < minHorizontal || x > maxHorizontal || y < minVertical || y > maxVertical)
        {
            CPH.SendMessage($"Fire command out of bounds. Horizontal: {minHorizontal} to {maxHorizontal}, Vertical: {minVertical} to {maxVertical}");
            return false;
        }

        // Check if user is subscribed
        if (!CPH.TwitchIsUserSubscribed(username))
        {
            CPH.SendMessage($"{username} is not a subscriber and cannot use the !fire command.");
            return false;
        }

        // Get subscription tier (0 for Prime, 1000, 2000, 3000 for Tier 1, 2, 3)
        int subscriptionTier = CPH.TwitchUserSubscriptionTier(username);
        int subscriptionLevel = (subscriptionTier / 1000) + 1; // Convert tier to level (1, 2, 3)

       if (TESTING) {
            CPH.SendMessage($"User {username} subtier: {subscriptionTier} subLevel: {subscriptionLevel}");
            return true;
        }
        
        // Fetch or create user data
        JObject userData = FetchOrCreateUserData(username, subscriptionLevel).Result;
        if (userData == null)
        {
            CPH.SendMessage($"Failed to fetch or create data for {username}.");
            return false;
        }

        int currentCredits = (int)userData["current_credits"];
        int creditsPerShot = GetCreditsPerShot(subscriptionLevel);

        int totalCost = creditsPerShot * z;
        if (currentCredits < totalCost)
        {
            CPH.SendMessage($"{username} doesn't have enough credits. Required: {totalCost}, Available: {currentCredits}");
            return false;
        }

        // Perform the fire action
        int shotsFired = DoFire(x, y, z);

        // Update user credits
        int creditsUsed = shotsFired * creditsPerShot;
        int remainingCredits = currentCredits - creditsUsed;
        UpdateUserCredits(username, remainingCredits).Wait();

        // Send messages
        CPH.SendWhisper(username, $"You have {remainingCredits} credits remaining.");
        CPH.SendMessage($"{username} fired {shotsFired} shots!");

        return true;
    }

    private async Task LoadGunConfig()
    {
        if (TESTING) {
            gunConfig = new JObject();
            gunConfig["min_horizontal"] = -90;
            gunConfig["max_horizontal"] = 90;
            gunConfig["min_vertical"] = -45;
            gunConfig["max_vertical"] = 45;
            return;
        }
        string response = await client.GetStringAsync($"{WORDPRESS_API_URL}/config");
        gunConfig = JObject.Parse(response);
    }

    private async Task<JObject> FetchOrCreateUserData(string username, int subscriptionLevel)
    {
        try
        {
            string response = await client.GetStringAsync($"{WORDPRESS_API_URL}/subscribers?user_id={username}");
            JArray users = JArray.Parse(response);
            
            if (users.Count > 0)
            {
                return (JObject)users[0];
            }
            else
            {
                // User not found, create new subscriber
                return await CreateNewSubscriber(username, subscriptionLevel);
            }
        }
        catch (HttpRequestException)
        {
            CPH.LogDebug($"Failed to fetch or create user data for {username}");
            return null;
        }
    }

    private async Task<JObject> CreateNewSubscriber(string username, int subscriptionLevel)
    {
        var newSubscriber = new
        {
            user_id = username,
            subscription_level = subscriptionLevel,
            current_credits = GetInitialCredits(subscriptionLevel),
            subscription_anniversary = DateTime.UtcNow.ToString("yyyy-MM-dd")
        };

        var content = new StringContent(JsonConvert.SerializeObject(newSubscriber), System.Text.Encoding.UTF8, "application/json");
        var response = await client.PostAsync($"{WORDPRESS_API_URL}/subscribers", content);

        if (response.IsSuccessStatusCode)
        {
            string responseContent = await response.Content.ReadAsStringAsync();
            return JObject.Parse(responseContent);
        }
        else
        {
            CPH.LogDebug($"Failed to create new subscriber {username}. Status code: {response.StatusCode}");
            return null;
        }
    }

    private int GetInitialCredits(int subscriptionLevel)
    {
        // This should ideally be fetched from the WordPress database
        switch (subscriptionLevel)
        {
            case 1: return 100;
            case 2: return 200;
            case 3: return 300;
            default: return 100;
        }
    }

    private int GetCreditsPerShot(int subscriptionLevel)
    {
        // This should be fetched from the WordPress database in a real implementation
        switch (subscriptionLevel)
        {
            case 1: return 10;
            case 2: return 8;
            case 3: return 6;
            default: return 10;
        }
    }

    private int DoFire(int x, int y, int z)
    {
        // This is a placeholder. In a real implementation, this would communicate with the GUNCTRL system
        CPH.LogInfo($"Firing: x={x}, y={y}, z={z}");
        return z; // Assume all shots are successful for this example
    }

    private async Task UpdateUserCredits(string username, int newCredits)
    {
        var content = new StringContent(JsonConvert.SerializeObject(new { current_credits = newCredits }));
        await client.PutAsync($"{WORDPRESS_API_URL}/subscribers?user_id={username}", content);
    }
}
